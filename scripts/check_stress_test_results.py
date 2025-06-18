#!/usr/bin/env python3
"""
Check stress test results and task statuses
"""

import requests
import json
import sys

def check_stress_test_results():
    """Check the final results of the stress test"""
    
    # Read the latest stress test results
    try:
        with open('stress_test_results_20250618_135238.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("No stress test results file found")
        return
    
    provider_id = data.get('provider_id')
    task_ids = data.get('task_ids', [])
    
    print(f"Provider ID: {provider_id}")
    print(f"Task IDs: {task_ids}")
    print()
    
    if not provider_id:
        print("No provider ID found in results")
        return
    
    # Check each task status
    for task_id in task_ids:
        print(f"=== Task {task_id} ===")
        
        # Get task details
        response = requests.get(f'http://localhost:8000/api/v1/tasks/{task_id}')
        if response.status_code == 200:
            task = response.json()
            print(f"Status: {task.get('status')}")
            print(f"Title: {task.get('title')}")
            
            # Check consensus data
            consensus_data = task.get('consensus_data', {})
            if consensus_data:
                print(f"Current Consensus: {consensus_data.get('current_consensus')}")
                print(f"Total Submissions: {consensus_data.get('total_submissions')}")
                print(f"Agreement Count: {consensus_data.get('agreement_count')}")
                print(f"Agreement Threshold: {consensus_data.get('agreement_threshold')}")
                print(f"Confidence Threshold: {consensus_data.get('confidence_threshold')}")
            else:
                print("No consensus data available")
            
            # Check results
            results_response = requests.get(f'http://localhost:8000/api/v1/tasks/{task_id}/results')
            if results_response.status_code == 200:
                results = results_response.json()
                print(f"Total Results: {len(results)}")
                
                if len(results) > 0:
                    # Count Yes/No responses
                    yes_count = 0
                    no_count = 0
                    for result in results:
                        result_data = result.get('result', {})
                        if isinstance(result_data, dict):
                            label = result_data.get('label', '')
                            if label == 'Yes':
                                yes_count += 1
                            elif label == 'No':
                                no_count += 1
                    
                    print(f"Yes responses: {yes_count}")
                    print(f"No responses: {no_count}")
                    print(f"Consensus ratio: {yes_count}/{len(results)} = {yes_count/len(results)*100:.1f}%")
                else:
                    print("No results available")
            else:
                print(f"Failed to get results: {results_response.status_code}")
        else:
            print(f"Failed to get task: {response.status_code}")
        
        print()

if __name__ == "__main__":
    check_stress_test_results() 