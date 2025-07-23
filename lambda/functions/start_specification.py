import json
import uuid
import logging
from datetime import datetime
from bedrock_client import BedrockClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda para iniciar nova especificação de feature
    """
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
            
        # Validar campos obrigatórios
        initial_idea = body.get('idea', '').strip()
        created_by = body.get('created_by', 'unknown')
        title = body.get('title', 'Nova Feature').strip()
        
        if not initial_idea:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Campo "idea" é obrigatório'
                }, ensure_ascii=False)
            }
        
        if len(initial_idea) < 10:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'A ideia deve ter pelo menos 10 caracteres'
                }, ensure_ascii=False)
            }
        
        # Gerar ID único
        spec_id = str(uuid.uuid4())
        
        # Inicializar cliente Bedrock
        bedrock_client = BedrockClient()
        
        # Gerar primeira pergunta
        first_question = bedrock_client.ask_specification_question(
            context=initial_idea,
            previous_answers={}
        )
        
        # Dados da especificação
        spec_data = {
            'spec_id': spec_id,
            'title': title,
            'initial_idea': initial_idea,
            'created_by': created_by,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'in_progress',
            'current_question': first_question,
            'questions_answers': {},
            'question_count': 1
        }
        
        logger.info(f"Especificação {spec_id} criada por {created_by}")
        logger.info(f"Primeira pergunta: {first_question}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'spec_id': spec_id,
                'title': title,
                'first_question': first_question,
                'question_number': 1,
                'status': 'started',
                'created_at': spec_data['created_at']
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"Erro na função start_specification: {str(e)}")
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
    test_event = {
        'body': json.dumps({
            'idea': 'Implementar PIX agendado para nossos clientes poderem programar pagamentos futuros',
            'created_by': 'test@okto.com',
            'title': 'PIX Agendado'
        })
    }
    
    result = lambda_handler(test_event, None)
    print("Status:", result['statusCode'])
    if result['statusCode'] == 200:
        response_data = json.loads(result['body'])
        print("Spec ID:", response_data['spec_id'])
        print("Primeira pergunta:", response_data['first_question'])
    else:
        print("Erro:", result['body'])