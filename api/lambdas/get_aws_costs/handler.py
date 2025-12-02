import json
import logging
import os
import boto3
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ce_client = boto3.client('ce')

def handler(event, context):
    """
    Fetch AWS costs for the last 30 days.
    """
    try:
        # Calculate date range (last 30 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Convert to string format YYYY-MM-DD
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"Fetching costs from {start_str} to {end_str}")
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_str,
                'End': end_str
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )
        
        # Process results
        results_by_time = response.get('ResultsByTime', [])
        
        formatted_data = {
            'start_date': start_str,
            'end_date': end_str,
            'last_updated': datetime.now().isoformat(),
            'daily_costs': []
        }
        
        total_cost = 0.0
        
        for day_result in results_by_time:
            date = day_result['TimePeriod']['Start']
            groups = day_result.get('Groups', [])
            
            day_data = {
                'date': date,
                'services': []
            }
            
            day_total = 0.0
            
            for group in groups:
                service_name = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                
                if amount > 0:
                    day_data['services'].append({
                        'service': service_name,
                        'cost': amount
                    })
                    day_total += amount
            
            day_data['total_cost'] = day_total
            formatted_data['daily_costs'].append(day_data)
            total_cost += day_total
            
        formatted_data['total_period_cost'] = total_cost
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(formatted_data)
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch costs: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
