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
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Validar campos obrigatórios
        spec_id = body.get('spec_id')
        current_question = body.get('current_question')
        answer = body.get('answer', '').strip()
        previous_answers = body.get('previous_answers', {})
        initial_idea = body.get('initial_idea', '')
        title = body.get('title', 'Feature')
        
        if not all([spec_id, current_question, answer]):
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Campos obrigatórios: spec_id, current_question, answer'
                }, ensure_ascii=False)
            }
        
        if len(answer) < 5:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'A resposta deve ter pelo menos 5 caracteres'
                }, ensure_ascii=False)
            }
        
        # Adicionar resposta atual ao histórico
        updated_answers = previous_answers.copy()
        updated_answers[current_question] = answer
        
        # Inicializar cliente Bedrock
        bedrock_client = BedrockClient()
        
        # Gerar próxima pergunta
        next_question = bedrock_client.ask_specification_question(
            context=initial_idea,
            previous_answers=updated_answers
        )
        
        # Verificar se especificação está completa
        is_complete = next_question.upper() == "ESPECIFICACAO_COMPLETA"
        
        if is_complete:
            # Especificação concluída - identificar stakeholders e gerar documento
            spec_data = {
                'spec_id': spec_id,
                'title': title,
                'initial_idea': initial_idea,
                'questions_answers': updated_answers,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Identificar stakeholders
            stakeholders_result = bedrock_client.identify_stakeholders(spec_data)
            stakeholders = stakeholders_result.get('stakeholders', [])
            
            # Gerar documento final
            final_document = bedrock_client.generate_final_document(spec_data)
            
            logger.info(f"Especificação {spec_id} concluída com {len(updated_answers)} perguntas")
            logger.info(f"Stakeholders identificados: {[s['area'] for s in stakeholders]}")
            
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
        logger.error(f"Erro na função process_answer: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Erro interno do servidor',
                'details': str(e)
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
        print("Status da spec:", response_data['status'])
        
        if response_data['status'] == 'completed':
            print("🎉 Especificação concluída!")
            print(f"Stakeholders: {[s['area'] for s in response_data['stakeholders']]}")
            print(f"Total de perguntas: {response_data['total_questions']}")
        else:
            print(f"Próxima pergunta: {response_data['next_question']}")
            print(f"Progresso: {response_data['progress']['percentage']}%")
    else:
        print("Erro:", result['body'])