import boto3
import json
import logging
from typing import Dict, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class BedrockClient:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
    
    def ask_specification_question(self, context: str, previous_answers: Dict) -> str:
        """
        Gera próxima pergunta baseada no contexto e respostas anteriores
        """
        try:
            # Montar histórico estruturado (usar os valores, não as chaves)
            qa_history = ""
            answered_categories = set()
            
            # CORREÇÃO: Usar apenas as respostas para identificar categorias
            for i, (question, answer) in enumerate(previous_answers.items(), 1):
                qa_history += f"P{i}: {question}\nR{i}: {answer}\n\n"
                
                # Identificar categorias baseado na PERGUNTA E RESPOSTA
                question_and_answer = (question + " " + answer).lower()
                
                if any(word in question_and_answer for word in ['negócio', 'objetivo', 'problema', 'cliente', 'receita', 'benefício', 'impacto']):
                    answered_categories.add('business')
                if any(word in question_and_answer for word in ['técnico', 'integração', 'sistema', 'api', 'backend', 'internet banking', 'pix']):
                    answered_categories.add('technical')
                if any(word in question_and_answer for word in ['compliance', 'bacen', 'regulament', 'audit', 'legal', 'segurança']):
                    answered_categories.add('compliance')
                if any(word in question_and_answer for word in ['ux', 'tela', 'fluxo', 'usuário', 'interface', 'experiência']):
                    answered_categories.add('ux')
                if any(word in question_and_answer for word in ['operacion', 'suporte', 'monitor', 'erro', 'rollback']):
                    answered_categories.add('operational')

            # Determinar próxima categoria necessária
            total_questions = len(previous_answers)
            
            # CORREÇÃO: Limitar a 5 perguntas máximo
            if total_questions >= 5:
                return "ESPECIFICACAO_COMPLETA"
            
            next_focus = self._get_next_category_focus(answered_categories, total_questions)
            
            prompt = f"""
CONTEXTO DA OKTO:
- Fintech brasileira para casas de apostas esportivas
- Sistemas: PIX (chave/QR/dados), pagamentos internos, cobranças, extratos, investimentos, rewards
- Stack: Next.js, Node.js, Keycloak (2FA), 3 roles (admin/assistant/operador)
- Times: Produto, PIX Backend, Internet Banking, Compliance, Financeiro, Suporte, TMS

FEATURE SOLICITADA: {context}

HISTÓRICO COMPLETO:
{qa_history}

CATEGORIAS JÁ COBERTAS: {list(answered_categories)}
TOTAL DE PERGUNTAS: {total_questions}

PRÓXIMO FOCO: {next_focus}

REGRAS CRÍTICAS:
1. Se já foram feitas 5+ perguntas, responda: "ESPECIFICACAO_COMPLETA"
2. NUNCA repita perguntas já feitas
3. Seja específico para o contexto OKTO e casas de apostas
4. Foque em informações práticas ainda não coletadas

Retorne APENAS a próxima pergunta relevante ou "ESPECIFICACAO_COMPLETA".
"""
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 150,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            question = result['content'][0]['text'].strip()
            
            # CORREÇÃO: Validação mais rigorosa de repetição
            if self._is_question_repetitive(question, previous_answers):
                logger.info("Pergunta repetitiva detectada, finalizando especificação")
                return "ESPECIFICACAO_COMPLETA"
            
            logger.info(f"Pergunta gerada: {question}")
            return question
            
        except Exception as e:
            logger.error(f"Erro ao gerar pergunta: {str(e)}")
            return "ESPECIFICACAO_COMPLETA"
    
    def _get_next_category_focus(self, answered_categories: set, total_questions: int) -> str:
        """Determina o foco da próxima pergunta baseado no que já foi coberto"""
        
        if total_questions == 0:
            return "OBJETIVO DE NEGÓCIO: Como esta feature beneficia as casas de apostas (nossos clientes)?"
        
        if total_questions == 1 and 'business' not in answered_categories:
            return "VALOR PARA OKTO: Qual o impacto esperado em receita, retenção ou operação?"
        
        if total_questions <= 2 and 'technical' not in answered_categories:
            return "ASPECTOS TÉCNICOS: Quais sistemas OKTO precisam alteração? (PIX Backend, Internet Banking, etc.)"
        
        if total_questions <= 3 and 'compliance' not in answered_categories:
            return "COMPLIANCE E SEGURANÇA: Há aspectos regulatórios do BACEN ou requisitos de segurança?"
        
        if total_questions <= 4 and 'ux' not in answered_categories:
            return "EXPERIÊNCIA DO USUÁRIO: Como funcionará para diferentes roles (admin/assistant/operador)?"
        
        return "ASPECTOS FINAIS: Há requisitos específicos não mencionados ou dependências críticas?"
    
    def _is_question_repetitive(self, new_question: str, previous_answers: Dict) -> bool:
        """Verifica se a pergunta é muito similar às já feitas"""
        new_question_lower = new_question.lower()
        
        # Palavras-chave principais da nova pergunta
        new_keywords = set([word for word in new_question_lower.split() 
                           if len(word) > 3 and word not in ['para', 'esta', 'como', 'qual', 'onde', 'quando']])
        
        for prev_question in previous_answers.keys():
            prev_question_lower = prev_question.lower()
            
            # Palavras-chave da pergunta anterior
            prev_keywords = set([word for word in prev_question_lower.split() 
                                if len(word) > 3 and word not in ['para', 'esta', 'como', 'qual', 'onde', 'quando']])
            
            # Verificar sobreposição de palavras-chave relevantes
            if len(new_keywords) > 0 and len(prev_keywords) > 0:
                overlap = len(new_keywords & prev_keywords)
                overlap_percentage = overlap / min(len(new_keywords), len(prev_keywords))
                
                # Se há 50%+ de sobreposição, é repetitiva
                if overlap_percentage > 0.5:
                    logger.info(f"Pergunta repetitiva detectada: {overlap_percentage:.2f} overlap")
                    return True
                    
        return False
    
    def identify_stakeholders(self, specification_data: Dict) -> Dict:
        """
        Identifica stakeholders necessários baseado na especificação completa
        """
        try:
            # Extrair informações relevantes
            answers_text = " ".join(specification_data.get('questions_answers', {}).values())
            feature_context = specification_data.get('initial_idea', '') + " " + answers_text
            
            prompt = f"""
CONTEXTO DA OKTO:
- Fintech para casas de apostas esportivas
- Times: Produto, PIX Backend, Internet Banking, Compliance, Financeiro, Suporte, TMS

ESPECIFICAÇÃO COMPLETA:
Título: {specification_data.get('title', '')}
Ideia: {specification_data.get('initial_idea', '')}
Respostas: {json.dumps(specification_data.get('questions_answers', {}), ensure_ascii=False)}

STAKEHOLDERS DISPONÍVEIS NA OKTO:
- PIX Backend: APIs PIX, integrações bancárias, processamento de pagamentos
- Internet Banking: Frontend, UX, autenticação, menus por role
- Compliance: Regulamentações BACEN, auditoria, prevenção à lavagem
- Financeiro: Fluxo de caixa, conciliação, custos operacionais, tarifas
- Suporte: Atendimento aos clientes (casas de apostas), documentação
- TMS: Monitoramento, logs, alertas, infraestrutura
- Produto: Roadmap, priorização, métricas de negócio

REGRAS:
1. Seja MUITO criterioso - apenas stakeholders realmente impactados
2. Considere que nossos clientes são casas de apostas
3. Analise impactos técnicos, regulatórios e operacionais específicos
4. Explique claramente POR QUE cada área precisa validar

Retorne JSON válido:
{
    "stakeholders": [
        {
            "area": "PIX Backend",
            "reason": "Explicação específica do impacto",
            "priority": "high|medium|low",
            "validation_focus": "O que especificamente precisa validar"
        }
    ]
}
"""
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            response_text = result['content'][0]['text'].strip()
            
            try:
                # Extrair JSON limpo
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = response_text[start:end]
                    stakeholders_data = json.loads(json_str)
                    
                    # Validar e filtrar stakeholders
                    valid_stakeholders = []
                    valid_areas = ["PIX Backend", "Internet Banking", "Compliance", "Financeiro", "Suporte", "TMS", "Produto"]
                    
                    for stakeholder in stakeholders_data.get('stakeholders', []):
                        if stakeholder.get('area') in valid_areas:
                            valid_stakeholders.append(stakeholder)
                    
                    result_data = {"stakeholders": valid_stakeholders}
                    logger.info(f"Stakeholders identificados: {[s['area'] for s in valid_stakeholders]}")
                    return result_data
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Erro ao parsear JSON da IA: {e}")
                
            # Fallback inteligente baseado no contexto
            return self._get_fallback_stakeholders(feature_context)
                
        except Exception as e:
            logger.error(f"Erro ao identificar stakeholders: {str(e)}")
            return self._get_fallback_stakeholders("")
    
    def _get_fallback_stakeholders(self, feature_context: str) -> Dict:
        """Fallback para identificar stakeholders baseado em palavras-chave"""
        stakeholders = []
        context_lower = feature_context.lower()
        
        # Internet Banking - para mudanças de interface/autenticação
        if any(word in context_lower for word in ['internet banking', 'login', 'facial', 'autenticação', 'interface', 'tela']):
            stakeholders.append({
                "area": "Internet Banking",
                "reason": "Alterações na interface e autenticação do usuário",
                "priority": "high",
                "validation_focus": "UX, integração com reconhecimento facial e impacto nas roles"
            })
        
        # PIX Backend - para features de pagamento
        if any(word in context_lower for word in ['pix', 'pagamento', 'transação', 'api']):
            stakeholders.append({
                "area": "PIX Backend",
                "reason": "Alterações em funcionalidades de pagamento",
                "priority": "high",
                "validation_focus": "Impacto nas APIs e processamento"
            })
        
        # Compliance - sempre para segurança
        if any(word in context_lower for word in ['segurança', 'facial', 'autenticação', 'biometria']):
            stakeholders.append({
                "area": "Compliance",
                "reason": "Validação de aspectos de segurança e conformidade",
                "priority": "high",
                "validation_focus": "Segurança biométrica e regulamentações"
            })
        
        # TMS - para monitoramento
        if any(word in context_lower for word in ['monitoramento', 'log', 'infraestrutura']):
            stakeholders.append({
                "area": "TMS",
                "reason": "Monitoramento e infraestrutura da nova funcionalidade",
                "priority": "medium",
                "validation_focus": "Logs, alertas e monitoramento"
            })
        
        # Suporte - sempre impactado
        stakeholders.append({
            "area": "Suporte",
            "reason": "Atendimento e documentação da nova funcionalidade", 
            "priority": "medium",
            "validation_focus": "Processos de suporte e troubleshooting"
        })
        
        return {"stakeholders": stakeholders}
    
    def generate_final_document(self, specification_data: Dict) -> str:
        """
        Gera documento final estruturado da especificação
        """
        try:
            title = specification_data.get('title', 'Nova Feature')
            initial_idea = specification_data.get('initial_idea', '')
            qa_pairs = specification_data.get('questions_answers', {})
            
            prompt = f"""
Gere um documento de especificação técnica completo para a OKTO.

DADOS:
Título: {title}
Ideia inicial: {initial_idea}
Perguntas e Respostas: {json.dumps(qa_pairs, ensure_ascii=False)}

CONTEXTO OKTO:
- Fintech para casas de apostas esportivas
- Stack: Next.js, Node.js, Keycloak 2FA
- Sistemas: PIX, pagamentos internos, cobranças, extratos, investimentos, rewards
- Roles: admin, assistant, operador

ESTRUTURA OBRIGATÓRIA (Markdown):

# SPEC-{specification_data.get('spec_id', 'XXX')[:8]}: {title}

## 📋 Resumo Executivo
- **Problema:** [problema específico para casas de apostas]
- **Solução:** [solução técnica proposta]  
- **Impacto esperado:** [benefícios quantificados]
- **Complexidade:** [alta/média/baixa com justificativa]

## 🎯 Objetivos de Negócio
[objetivos específicos e mensuráveis para o contexto OKTO]

## 👥 Impacto nos Clientes (Casas de Apostas)
[como beneficia nossos clientes especificamente]

## ⚙️ Especificação Técnica

### Sistemas OKTO Impactados
[PIX Backend, Internet Banking, BackOffice, etc.]

### Funcionalidades Core
[lista detalhada das funcionalidades]

### Regras de Negócio
[regras específicas, limites, validações]

### Integrações Necessárias
[APIs, serviços externos, sistemas internos]

## 🔒 Compliance e Segurança
[aspectos BACEN, auditoria, segurança]

## 📱 Experiência do Usuário

### Por Role de Usuário
- **Admin:** [funcionalidades específicas]
- **Assistant:** [funcionalidades específicas] 
- **Operador:** [funcionalidades específicas]

### Fluxos Principais
[jornadas do usuário]

## 🔧 Considerações Técnicas
[arquitetura, performance, escalabilidade]

## 📊 Métricas de Sucesso
[KPIs específicos para medir sucesso]

## ⚠️ Riscos e Mitigações
[riscos técnicos, de negócio e como mitigar]

## 🚀 Plano de Implementação
[fases, cronograma, dependências]

Seja específico para o contexto OKTO e casas de apostas. Use informações das respostas fornecidas.
"""
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2500,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            document = result['content'][0]['text'].strip()
            
            logger.info("Documento final gerado com sucesso")
            return document
            
        except Exception as e:
            logger.error(f"Erro ao gerar documento final: {str(e)}")
            return f"# Erro ao Gerar Documento\n\nErro: {str(e)}\n\nTente novamente ou entre em contato com o suporte."