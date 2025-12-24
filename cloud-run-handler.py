#!/usr/bin/env python3
"""
Cloud Run HTTP Handler for LinkedIn Outreach Automation

This handler receives HTTP requests and triggers batch processing.
Designed to work with Cloud Scheduler for scheduled runs.
"""

import os
import json
import logging
from flask import Flask, request, jsonify, render_template
from batch_processor import BatchProcessor

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COOKIE_FILE = 'linkedin_cookies.json'


def get_cookies_from_env():
    """Get LinkedIn cookies from environment variables (more secure)."""
    li_at = os.environ.get('LINKEDIN_LI_AT')
    if li_at:
        return {
            'li_at': li_at,
            'JSESSIONID': os.environ.get('LINKEDIN_JSESSIONID', '')
        }
    return None


def check_cookies_configured():
    """Check if LinkedIn cookies are configured (env vars or file)."""
    if get_cookies_from_env():
        return True
    return os.path.exists(COOKIE_FILE)


@app.route('/', methods=['GET'])
def index():
    """Serve the frontend."""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def api_status():
    """API status endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'linkedin-outreach-automation',
        'cookies_configured': check_cookies_configured()
    }), 200


@app.route('/api/cookies/status', methods=['GET'])
def cookies_status():
    """Check if cookies are configured."""
    return jsonify({
        'configured': check_cookies_configured()
    }), 200


@app.route('/api/cookies', methods=['POST'])
def save_cookies():
    """Save LinkedIn cookies."""
    try:
        data = request.get_json() or {}
        li_at = data.get('li_at', '').strip()
        jsessionid = data.get('JSESSIONID', '').strip()
        
        if not li_at:
            return jsonify({'error': 'li_at cookie is required'}), 400
        
        cookie_data = {
            'li_at': li_at
        }
        if jsessionid:
            cookie_data['JSESSIONID'] = jsessionid
        
        with open(COOKIE_FILE, 'w') as f:
            json.dump(cookie_data, f, indent=2)
        
        logger.info("LinkedIn cookies saved successfully")
        return jsonify({'status': 'success', 'message': 'Cookies saved'}), 200
        
    except Exception as e:
        logger.error(f"Error saving cookies: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/run', methods=['POST'])
def run_batch():
    """
    Trigger batch processing.
    
    Expected JSON body:
    {
        "profiles": ["url1", "url2", ...],
        "profiles_file": "profiles_batch.txt",  # Optional
        "send_messages": true,
        "skip_scraping": false,
        "skip_annotation": false,
        "skip_screenshot": false
    }
    """
    try:
        data = request.get_json() or {}
        
        # Get profiles from request
        profiles = data.get('profiles', [])
        profiles_file = data.get('profiles_file')
        
        if not profiles and not profiles_file:
            return jsonify({
                'error': 'Must provide either "profiles" array or "profiles_file"'
            }), 400
        
        # Load profiles if file provided
        processor = BatchProcessor(
            delay_between_profiles=int(data.get('delay_profiles', 30)),
            delay_between_messages=int(data.get('delay_messages', 60))
        )
        
        if profiles_file:
            if not os.path.exists(profiles_file):
                return jsonify({
                    'error': f'Profiles file not found: {profiles_file}'
                }), 404
            profile_urls = processor.load_profiles_from_file(profiles_file)
        else:
            profile_urls = [processor.normalize_profile_url(url) for url in profiles]
        
        if not profile_urls:
            return jsonify({
                'error': 'No valid profile URLs found'
            }), 400
        
        # Process batch
        logger.info(f"Starting batch processing for {len(profile_urls)} profiles")
        result = processor.process_batch(
            profile_urls,
            send_messages=data.get('send_messages', True),
            skip_scraping=data.get('skip_scraping', False),
            skip_annotation=data.get('skip_annotation', False),
            skip_screenshot=data.get('skip_screenshot', False)
        )
        
        return jsonify({
            'status': 'success',
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e),
            'status': 'failed'
        }), 500


@app.route('/run-file', methods=['POST'])
def run_from_file():
    """
    Run batch processing from a profiles file in Cloud Storage or local.
    
    Expected JSON body:
    {
        "profiles_file": "gs://bucket/profiles.txt" or "profiles_batch.txt",
        "send_messages": true
    }
    """
    try:
        data = request.get_json() or {}
        profiles_file = data.get('profiles_file', 'profiles_batch.txt')
        
        # Download from GCS if needed
        if profiles_file.startswith('gs://'):
            import subprocess
            local_file = '/tmp/profiles.txt'
            subprocess.run(['gsutil', 'cp', profiles_file, local_file], check=True)
            profiles_file = local_file
        
        processor = BatchProcessor()
        profile_urls = processor.load_profiles_from_file(profiles_file)
        
        if not profile_urls:
            return jsonify({'error': 'No profiles found'}), 400
        
        result = processor.process_batch(
            profile_urls,
            send_messages=data.get('send_messages', True)
        )
        
        return jsonify({
            'status': 'success',
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

