#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
헤로쿠 웹훅 수신 서버
TradingView에서 웹훅을 받아서 로컬 애플리케이션으로 전달
"""

import os
import json
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 환경 변수에서 로컬 서버 URL 가져오기 (기본값: localhost)
LOCAL_SERVER_URL = os.environ.get('LOCAL_SERVER_URL', 'http://localhost:8081')

@app.route('/', methods=['GET'])
def home():
    """서버 상태 확인"""
    return jsonify({
        'status': 'Heroku Webhook Server Running',
        'timestamp': time.time(),
        'local_server': LOCAL_SERVER_URL,
        'message': 'Ready to receive TradingView webhooks'
    })

@app.route('/webhook', methods=['POST'])
def webhook_endpoint():
    """TradingView 웹훅 수신 엔드포인트"""
    try:
        # 클라이언트 IP 및 User-Agent 로깅
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        logger.info(f"웹훅 수신 - IP: {client_ip}, User-Agent: {user_agent}")
        
        # 요청 데이터 수신
        content_type = request.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            webhook_data = request.get_json()
        else:
            # TradingView가 때로는 form-data로 보낼 수 있음
            webhook_data = request.form.to_dict()
            if not webhook_data:
                # Raw text로 시도
                raw_data = request.get_data(as_text=True)
                try:
                    webhook_data = json.loads(raw_data)
                except:
                    webhook_data = {'message': raw_data}
        
        # 타임스탬프 추가
        webhook_data['heroku_received_at'] = time.time()
        webhook_data['heroku_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S UTC')
        webhook_data['client_ip'] = client_ip
        
        logger.info(f"웹훅 데이터 수신: {webhook_data}")
        
        # 로컬 서버로 전달 시도
        local_success = False
        local_error = None
        
        try:
            # 로컬 서버로 웹훅 데이터 전달
            response = requests.post(
                f"{LOCAL_SERVER_URL}/webhook",
                json=webhook_data,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                local_success = True
                logger.info(f"로컬 서버 전달 성공: {response.status_code}")
            else:
                local_error = f"로컬 서버 응답 오류: {response.status_code}"
                logger.warning(local_error)
                
        except requests.exceptions.RequestException as e:
            local_error = f"로컬 서버 연결 실패: {str(e)}"
            logger.error(local_error)
        
        # 응답 생성
        response_data = {
            'success': True,
            'message': '헤로쿠에서 웹훅 수신 완료',
            'timestamp': time.time(),
            'data_received': webhook_data,
            'local_delivery': {
                'success': local_success,
                'error': local_error,
                'target_url': LOCAL_SERVER_URL
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"웹훅 처리 오류: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '웹훅 처리 중 오류 발생'
        }), 500

@app.route('/test', methods=['POST', 'GET'])
def test_webhook():
    """웹훅 테스트 엔드포인트"""
    test_data = {
        'symbol': 'BTCUSDT',
        'action': 'buy',
        'price': 45000,
        'strategy': 'test_strategy',
        'timestamp': time.time(),
        'test': True,
        'source': 'heroku_test'
    }
    
    # 로컬 서버로 테스트 데이터 전달
    try:
        response = requests.post(
            f"{LOCAL_SERVER_URL}/webhook",
            json=test_data,
            timeout=10
        )
        
        return jsonify({
            'success': True,
            'message': '테스트 웹훅 전송 완료',
            'test_data': test_data,
            'local_response': response.status_code if response else 'No response'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '테스트 웹훅 전송 실패',
            'test_data': test_data
        })

@app.route('/status', methods=['GET'])
def status():
    """서버 상태 및 설정 정보"""
    return jsonify({
        'server': 'Heroku Webhook Relay',
        'status': 'running',
        'local_server_url': LOCAL_SERVER_URL,
        'endpoints': {
            'webhook': '/webhook (POST)',
            'test': '/test (POST/GET)',
            'status': '/status (GET)'
        },
        'timestamp': time.time(),
        'environment': 'heroku' if 'DYNO' in os.environ else 'local'
    })

# 에러 핸들러
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'Available endpoints: /, /webhook, /test, /status'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on the server'
    }), 500

if __name__ == '__main__':
    # 로컬 실행용
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 헤로쿠 웹훅 서버 시작")
    print(f"📡 포트: {port}")
    print(f"🔗 로컬 서버: {LOCAL_SERVER_URL}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )