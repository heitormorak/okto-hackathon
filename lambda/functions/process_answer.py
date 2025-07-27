import json
import logging
from datetime import datetime, timezone
from bedrock_client import BedrockClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda para processar resposta e gerar próxima pergunta
    """
    try:
        # Parse flexível do request
        logger.info(f"Event recebido: {json.dumps(event)}")
        
        # Tentar diferentes formatos de parsing
        if isinstance(event.get('body'), str):
            # Via API Gateway com body string
            body = json.loads(event['body'])
            logger.info("Parsed from string body")
        elif isinstance(event.get('body'), dict):
            # Via teste direto com body dict
            body = event['body']
            logger.info("Using dict body")
        elif 'spec_id' in event:
            # Dados diretos no event (sem wrapper body)
            body = event
            logger.info("Using direct event data")
        else:
            # Fallback para body dict
            body = event.get('body', {})
            logger.info("Using fallback body")
        
        logger.info(f"Body processado: {json.dumps(body)}")
        
        # Validar campos obrigatórios com fallbacks inteligentes
        spec_id = body.get('spec_id')
        current_question = body.get('current_question')
        answer = body.get('answer', '').strip()
        previous_answers = body.get('previous_answers', {})
        initial_idea = body.get('initial_idea', '')
        title = body.get('title', 'Feature')
        
        # Log dos campos extraídos
        logger.info(f"Campos extraídos - spec_id: {spec_id}, current_question: {current_question}, answer: {answer}")
        
        # Validações
        if not spec_id:
            logger.error("spec_id não encontrado")
            return create_error_response('Campo "spec_id" é obrigatório')
        
        if not current_question:
            logger.error("current_question não encontrado")
            return create_error_response('Campo "current_question" é obrigatório')
        
        if not answer:
            logger.error("answer não encontrado ou vazio")
            return create_error_response('Campo "answer" é obrigatório')
        
        if len(answer) < 5:
            logger.error(f"answer muito curto: {len(answer)} caracteres")
            return create_error_response('A resposta deve ter pelo menos 5 caracteres')
        
        # Adicionar resposta atual ao histórico
        updated_answers = previous_answers.copy()
        updated_answers[current_question] = answer
        
        logger.info(f"Histórico atualizado: {len(updated_answers)} respostas")
        
        # Inicializar cliente Bedrock
        try:
            bedrock_client = BedrockClient()
            logger.info("BedrockClient inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar BedrockClient: {str(e)}")
            return create_error_response(f'Erro ao conectar com IA: {str(e)}')
        
        # Gerar próxima pergunta
        try:
            logger.info("Gerando próxima pergunta...")
            next_question = bedrock_client.ask_specification_question(
                context=initial_idea,
                previous_answers=updated_answers
            )
            logger.info(f"Próxima pergunta gerada: {next_question}")
        except Exception as e:
            logger.error(f"Erro ao gerar próxima pergunta: {str(e)}")
            return create_error_response(f'Erro na IA: {str(e)}')
        
        # Verificar se especificação está completa
        is_complete = next_question.upper() == "ESPECIFICACAO_COMPLETA"
        
        if is_complete:
            logger.info("Especificação marcada como completa")
            # Especificação concluída - identificar stakeholders e gerar documento
            spec_data = {
                'spec_id': spec_id,
                'title': title,
                'initial_idea': initial_idea,
                'questions_answers': updated_answers,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            try:
                # Identificar stakeholders
                logger.info("Identificando stakeholders...")
                stakeholders_result = bedrock_client.identify_stakeholders(spec_data)
                stakeholders = stakeholders_result.get('stakeholders', [])
                logger.info(f"Stakeholders identificados: {len(stakeholders)}")
                
                # Gerar documento final
                logger.info("Gerando documento final...")
                final_document = bedrock_client.generate_final_document(spec_data)
                logger.info("Documento gerado com sucesso")
                
                logger.info(f"Especificação {spec_id} concluída com {len(updated_answers)} perguntas")
                logger.info(f"Stakeholders identificados: {[s.get('area', 'Unknown') for s in stakeholders]}")
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({
                        'spec_id': spec_id,
                        'status': 'completed',
                        'stakeholders': stakeholders,
                        'final_document': final_document,
                        'total_questions': len(updated_answers),
                        'all_answers': updated_answers,
                        'completed_at': spec_data['completed_at'],
                        'summary': {
                            'title': title,
                            'idea': initial_idea,
                            'stakeholder_count': len(stakeholders),
                            'questions_count': len(updated_answers)
                        }
                    }, ensure_ascii=False)
                }
                
            except Exception as e:
                logger.error(f"Erro ao finalizar especificação: {str(e)}")
                return create_error_response(f'Erro ao finalizar especificação: {str(e)}')
        else:
            # Continuar com próxima pergunta
            question_number = len(updated_answers) + 1
            
            # Estimar progresso (geralmente leva 4-7 perguntas)
            estimated_total = 6
            progress_percentage = min(int((len(updated_answers) / estimated_total) * 100), 90)
            
            logger.info(f"Especificação {spec_id} - Pergunta {question_number}: {next_question}")
            
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'spec_id': spec_id,
                    'status': 'in_progress',
                    'next_question': next_question,
                    'question_number': question_number,
                    'previous_answers': updated_answers,
                    'progress': {
                        'current': len(updated_answers),
                        'estimated_total': estimated_total,
                        'percentage': progress_percentage
                    }
                }, ensure_ascii=False)
            }
        
    except Exception as e:
        logger.error(f"Erro geral na função process_answer: {str(e)}")
        logger.error(f"Event completo: {json.dumps(event)}")
        return create_error_response(f'Erro interno: {str(e)}')

def create_error_response(message):
    """Função helper para criar respostas de erro padronizadas"""
    return {
        'statusCode': 400,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'error': message
        }, ensure_ascii=False)
    }

# Para testar localmente
if __name__ == "__main__":
    # Simular uma resposta à primeira pergunta
    test_event = {
        'body': json.dumps({
            'spec_id': 'test-123',
            'current_question': 'Quais tipos de PIX devem ser suportados (CPF, CNPJ, chave, QR Code) e há limites de valor?',
            'answer': 'Deve suportar todos os tipos: CPF, CNPJ, chave PIX e QR Code. Limite de R$ 50.000 por transação, funcionando 24/7 incluindo finais de semana',
            'previous_answers': {},
            'initial_idea': 'Implementar PIX agendado para nossos clientes poderem programar pagamentos futuros',
            'title': 'PIX Agendado'
        })
    }
    
    result = lambda_handler(test_event, None)
    print("Status:", result['statusCode'])
    
    if result['statusCode'] == 200:
        response_data = json.loads(result['body'])
        print("Status da spec:", response_data.get('status'))
        
        if response_data.get('status') == 'completed':
            print("🎉 Especificação concluída!")
            print(f"Stakeholders: {[s.get('area') for s in response_data.get('stakeholders', [])]}")
            print(f"Total de perguntas: {response_data.get('total_questions')}")
        else:
            print(f"Próxima pergunta: {response_data.get('next_question')}")
            print(f"Progresso: {response_data.get('progress', {}).get('percentage')}%")
    else:
        print("Erro:", result['body'])