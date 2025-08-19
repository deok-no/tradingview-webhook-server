const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 5000;

// 환경 변수에서 로컬 서버 URL 가져오기
const LOCAL_SERVER_URL = process.env.LOCAL_SERVER_URL || 'http://localhost:8081';

// 미들웨어 설정
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 로깅 미들웨어
app.use((req, res, next) => {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${req.method} ${req.path} - IP: ${req.ip}`);
    next();
});

// 홈 페이지 - 서버 상태 확인
app.get('/', (req, res) => {
    res.json({
        status: 'Heroku Node.js Webhook Server Running',
        timestamp: new Date().toISOString(),
        local_server: LOCAL_SERVER_URL,
        message: 'Ready to receive TradingView webhooks'
    });
});

// 웹훅 수신 엔드포인트
app.post('/webhook', async (req, res) => {
    try {
        // 클라이언트 정보 로깅
        const clientIp = req.headers['x-forwarded-for'] || req.connection.remoteAddress;
        const userAgent = req.headers['user-agent'] || 'Unknown';
        
        console.log(`웹훅 수신 - IP: ${clientIp}, User-Agent: ${userAgent}`);
        
        // 웹훅 데이터 수신
        let webhookData = req.body;
        
        // 빈 데이터인 경우 raw body 확인
        if (!webhookData || Object.keys(webhookData).length === 0) {
            webhookData = { message: 'Empty webhook received' };
        }
        
        // 메타데이터 추가
        webhookData.heroku_received_at = Date.now();
        webhookData.heroku_timestamp = new Date().toISOString();
        webhookData.client_ip = clientIp;
        webhookData.server_type = 'nodejs';
        
        console.log('웹훅 데이터 수신:', JSON.stringify(webhookData, null, 2));
        
        // 로컬 서버로 전달
        let localSuccess = false;
        let localError = null;
        
        try {
            // Electron 내부 웹훅 서버로 직접 전달 (포트 3000)
            const electronUrl = LOCAL_SERVER_URL.replace(':8081', ':3000');
            const response = await axios.post(`${electronUrl}/internal-webhook`, {
                type: 'webhook_signal',
                data: webhookData,
                source: 'heroku',
                received_at: Date.now()
            }, {
                timeout: 10000,
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.status === 200) {
                localSuccess = true;
                console.log(`로컬 서버 전달 성공: ${response.status}`);
            } else {
                localError = `로컬 서버 응답 오류: ${response.status}`;
                console.warn(localError);
            }
            
        } catch (error) {
            localError = `로컬 서버 연결 실패: ${error.message}`;
            console.error(localError);
        }
        
        // 응답 생성
        const responseData = {
            success: true,
            message: '헤로쿠에서 웹훅 수신 완료',
            timestamp: Date.now(),
            data_received: webhookData,
            local_delivery: {
                success: localSuccess,
                error: localError,
                target_url: LOCAL_SERVER_URL
            }
        };
        
        res.status(200).json(responseData);
        
    } catch (error) {
        console.error('웹훅 처리 오류:', error);
        res.status(500).json({
            success: false,
            error: error.message,
            message: '웹훅 처리 중 오류 발생'
        });
    }
});

// 테스트 웹훅 엔드포인트
app.all('/test', async (req, res) => {
    const testData = {
        symbol: 'BTCUSDT',
        action: 'buy',
        price: 45000,
        strategy: 'test_strategy',
        timestamp: Date.now(),
        test: true,
        source: 'heroku_nodejs_test'
    };
    
    try {
        const response = await axios.post(`${LOCAL_SERVER_URL}/webhook`, testData, {
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        res.json({
            success: true,
            message: '테스트 웹훅 전송 완료',
            test_data: testData,
            local_response: response.status
        });
        
    } catch (error) {
        res.json({
            success: false,
            error: error.message,
            message: '테스트 웹훅 전송 실패',
            test_data: testData
        });
    }
});

// 상태 확인 엔드포인트
app.get('/status', (req, res) => {
    res.json({
        server: 'Heroku Node.js Webhook Relay',
        status: 'running',
        local_server_url: LOCAL_SERVER_URL,
        endpoints: {
            webhook: '/webhook (POST)',
            test: '/test (POST/GET)',
            status: '/status (GET)'
        },
        timestamp: Date.now(),
        environment: process.env.NODE_ENV || 'production',
        uptime: process.uptime()
    });
});

// 404 핸들러
app.use('*', (req, res) => {
    res.status(404).json({
        error: 'Endpoint not found',
        message: 'Available endpoints: /, /webhook, /test, /status'
    });
});

// 에러 핸들러
app.use((error, req, res, next) => {
    console.error('서버 오류:', error);
    res.status(500).json({
        error: 'Internal server error',
        message: 'Something went wrong on the server'
    });
});

// 서버 시작
app.listen(PORT, '0.0.0.0', () => {
    console.log('🚀 헤로쿠 Node.js 웹훅 서버 시작');
    console.log(`📡 포트: ${PORT}`);
    console.log(`🔗 로컬 서버: ${LOCAL_SERVER_URL}`);
    console.log(`🌐 서버 실행: http://0.0.0.0:${PORT}`);
});