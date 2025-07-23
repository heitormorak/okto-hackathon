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
            # Montar histórico de perguntas e respostas
            qa_history = ""
            for i, (question, answer) in enumerate(previous_answers.items(), 1):
                qa_history += f"{i}. P: {question}\n   R: {answer}\n\n"
            
            prompt = f"""
            Você é um especialista em especificação de features para a OKTO Payments, uma fintech brasileira.
            
            CONTEXTO DA FEATURE: {context}
            
            PERGUNTAS JÁ RESPONDIDAS:
            {qa_history}
            
            Sua tarefa é fazer a próxima pergunta mais importante para completar a especificação.
            
            DIRETRIZES:
            - Foque em aspectos não cobertos ainda
            - Considere o contexto de pagamentos/fintech brasileiro
            - Seja específico sobre regras de negócio
            - Pense em integrações necessárias
            - Considere aspectos de compliance (BACEN, LGPD)
            - Se já tem informações suficientes, responda: "ESPECIFICACAO_COMPLETA"
            
            TIPOS DE PERGUNTA POR CATEGORIA:
            - Negócio: objetivos, métricas, usuários-alvo
            - Técnico: integrações, performance, arquitetura
            - UX: fluxos, validações, mensagens de erro
            - Compliance: regulamentações, auditoria, segurança
            - Operacional: suporte, monitoramento, rollback
            
            Retorne APENAS a próxima pergunta, sem explicações.
            """
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            question = result['content'][0]['text'].strip()
            
            logger.info(f"Pergunta gerada: {question}")
            return question
            
        except Exception as e:
            logger.error(f"Erro ao gerar pergunta: {str(e)}")
            return "Erro ao gerar pergunta. Tente novamente."
    
    def identify_stakeholders(self, specification_data: Dict) -> Dict:
        """
        Identifica stakeholders necessários baseado na especificação completa
        """
        try:
            prompt = f"""
            Baseado na especificação completa abaixo, identifique TODOS os stakeholders da OKTO que precisam aprovar esta feature:
            
            ESPECIFICAÇÃO:
            {json.dumps(specification_data, indent=2, ensure_ascii=False)}
            
            STAKEHOLDERS POSSÍVEIS NA OKTO:
            - Compliance: regulamentações, BACEN, LGPD, auditoria
            - Financeiro: impacto em fluxo de caixa, conciliação, custos
            - UX: experiência do usuário, design, usabilidade
            - Backend: desenvolvimento de APIs, integrações, arquitetura
            - Frontend: interfaces, componentes, responsividade
            - QA: testes, cenários, automação
            - Suporte: atendimento, documentação, FAQ
            - Comercial: impacto em vendas, pricing, estratégia
            - RH: impacto em operações internas, treinamentos
            - Jurídico: contratos, termos de uso, responsabilidades
            
            REGRAS:
            - Seja criterioso: apenas stakeholders realmente impactados
            - Explique claramente POR QUE cada um precisa aprovar
            - Considere o contexto específico da OKTO (fintech/pagamentos)
            
            Retorne APENAS um JSON válido no formato:
            {
                "stakeholders": [
                    {
                        "area": "Compliance",
                        "reason": "Precisa validar conformidade com regulamentações do BACEN para PIX",
                        "priority": "high"
                    },
                    {
                        "area": "UX", 
                        "reason": "Precisa desenhar fluxo de agendamento e cancelamento",
                        "priority": "high"
                    }
                ]
            }
            """
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 800,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            response_text = result['content'][0]['text'].strip()
            
            # Extrair JSON da resposta
            try:
                # Procurar por JSON válido na resposta
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                
                stakeholders_data = json.loads(json_str)
                logger.info(f"Stakeholders identificados: {len(stakeholders_data['stakeholders'])}")
                return stakeholders_data
                
            except json.JSONDecodeError:
                logger.warning("Não foi possível extrair JSON da resposta da IA")
                # Fallback com stakeholders padrão
                return {
                    "stakeholders": [
                        {"area": "Backend", "reason": "Nova funcionalidade técnica", "priority": "high"},
                        {"area": "UX", "reason": "Impacto na experiência do usuário", "priority": "medium"}
                    ]
                }
                
        except Exception as e:
            logger.error(f"Erro ao identificar stakeholders: {str(e)}")
            return {
                "stakeholders": [
                    {"area": "Backend", "reason": "Nova funcionalidade técnica", "priority": "high"}
                ]
            }
    
    def generate_final_document(self, specification_data: Dict) -> str:
        """
        Gera documento final estruturado da especificação
        """
        try:
            prompt = f"""
            Baseado na especificação completa, gere um documento estruturado no formato Markdown para a OKTO.
            
            DADOS DA ESPECIFICAÇÃO:
            {json.dumps(specification_data, indent=2, ensure_ascii=False)}
            
            ESTRUTURA OBRIGATÓRIA:
            # SPEC-[ID]: [Título da Feature]
            
            ## 📋 Resumo Executivo
            - **Problema:** [problema que resolve]
            - **Solução:** [solução proposta]
            - **Impacto esperado:** [benefícios quantificados]
            - **Complexidade:** [alta/média/baixa]
            
            ## 🎯 Objetivos de Negócio
            [objetivos claros e mensuráveis]
            
            ## 👥 Personas e Casos de Uso
            [quem vai usar e como]
            
            ## ⚙️ Especificação Funcional
            ### Funcionalidades Core
            [lista detalhada das funcionalidades]
            
            ### Regras de Negócio
            [regras específicas e validações]
            
            ### Integrações Necessárias
            [sistemas e APIs que precisa integrar]
            
            ## 🔒 Aspectos de Segurança e Compliance
            [considerações de segurança, LGPD, BACEN]
            
            ## 📱 Especificação de UX
            [fluxos, telas, componentes]
            
            ## 🔧 Considerações Técnicas
            [arquitetura, performance, escalabilidade]
            
            ## 🧪 Cenários de Teste
            [casos de teste principais]
            
            ## 📊 Métricas de Sucesso
            [KPIs para medir sucesso]
            
            ## ⚠️ Riscos e Mitigações
            [riscos identificados e como mitigar]
            
            ## 🚀 Plano de Rollout
            [estratégia de lançamento]
            
            Seja específico, técnico e completo. Use markdown bem formatado.
            """
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            document = result['content'][0]['text'].strip()
            
            logger.info("Documento final gerado com sucesso")
            return document
            
        except Exception as e:
            logger.error(f"Erro ao gerar documento final: {str(e)}")
            return f"Erro ao gerar documento: {str(e)}"