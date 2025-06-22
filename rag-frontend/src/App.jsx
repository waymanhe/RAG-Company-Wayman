import { useState } from 'react'
import axios from 'axios'
import { App as AntApp, Input, Button, Card, Typography, Space, Spin, Alert, List, Collapse } from 'antd'
import { RocketOutlined } from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

// 配置axios实例，设置后端的base URL
const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
})

function App() {
  // --- State Management ---
  const [query, setQuery] = useState('中芯国际的2024年主营业务是多少？')
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  // --- API Call Handler ---
  const handleGenerateAnswer = async () => {
    if (!query.trim()) {
      setError('请输入问题。')
      return
    }
    setIsLoading(true)
    setResult(null)
    setError('')

    try {
      const response = await apiClient.post('/api/ask', { query })
      setResult(response.data)
    } catch (err) {
      setError('请求失败，请检查后端服务是否正在运行或查看控制台日志。')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }
  
  const headerStyle = {
    background: 'linear-gradient(to right, #8a2be2, #ff69b4)',
    color: 'white',
    padding: '30px',
    borderRadius: '8px',
    marginBottom: '20px',
  }

  const cardStyle = {
    marginBottom: '15px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
  }

  const siderStyle = {
    background: '#fff',
    borderRight: '1px solid #f0f0f0',
    padding: '30px',
    flex: '0 0 30%',
    minWidth: 320,
  }

  const contentStyle = {
    flex: '1 1 60%',
    padding: '20px',
    overflowY: 'auto',
    height: '100vh',
  }

  return (
    <AntApp>
      <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden' }}>
        <div style={siderStyle}>
          <Title level={5} style={{ fontSize: '14px', fontWeight: 'bold' }}>查询设置</Title>
          <Text style={{ fontSize: '12px', color: '#666', marginTop: '15px', marginBottom: '5px', display: 'block' }}>输入问题</Text>
          <TextArea
            rows={4}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入问题"
            style={{ height: 'auto', borderColor: '#ccc' }}
          />
          <Button
            type="default"
            onClick={handleGenerateAnswer}
            loading={isLoading}
            style={{ width: '100%', height: '40px', marginTop: '10px', backgroundColor: '#f0f0f0' }}
          >
            生成答案
          </Button>
        </div>
        <div style={contentStyle}>
          <div style={headerStyle}>
            <Title level={3} style={{ color: 'white', fontSize: '20px', margin: 0 }}>🚀 RAG Challenge </Title>
            <Paragraph style={{ color: 'white', fontSize: '12px', margin: '5px 0 0 0', opacity: 0.9 }}>
              基于深度RAG系统 | 支持多年公司年报问答 | 向量检索+LLM整理 | 帮忙点个小星星
            </Paragraph>
          </div>
          
          <Spin spinning={isLoading} tip="加载中..." size="large" style={{ display: 'block' }}>
            {error && <Alert message={error} type="error" showIcon style={{marginBottom: '15px'}} />}
            {result && (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card title={<Title level={5} style={{fontSize: '14px'}}>检索结果</Title>} style={cardStyle} styles={{ body: { padding: '15px' } }}>
                  {/* This card can be used for general search status if needed */}
                </Card>
                <Card title={<Title level={5} style={{fontSize: '14px'}}>分步推理:</Title>} style={{ ...cardStyle, backgroundColor: '#e6f7ff' }} styles={{ body: { padding: '15px' } }}>
                  <List
                    dataSource={result.reasoning_steps}
                    renderItem={(item, index) => (
                      <List.Item style={{padding: '0 0 10px 0', border: 'none'}}>
                        <Text>{index + 1}. {item}</Text>
                      </List.Item>
                    )}
                    split={false}
                  />
                </Card>
                <Card title={<Title level={5} style={{fontSize: '14px'}}>推理摘要:</Title>} style={{ ...cardStyle, backgroundColor: '#e6ffe6' }} styles={{ body: { padding: '15px' } }}>
                  <Paragraph style={{margin: 0}}>{result.reasoning_summary}</Paragraph>
                </Card>
                <Card title={<Title level={5} style={{fontSize: '14px'}}>相关页面:</Title>} style={cardStyle} styles={{ body: { padding: '15px' } }}>
                  <Collapse ghost>
                    <Collapse.Panel header="点击查看/折叠详细上下文" key="1">
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', backgroundColor: '#fafafa', padding: '10px', borderRadius: '4px' }}>
                        {JSON.stringify(result.raw_context, null, 2)}
                      </pre>
                    </Collapse.Panel>
                  </Collapse>
                </Card>
                <Card title={<Title level={5} style={{fontSize: '14px'}}>最终答案:</Title>} style={{ ...cardStyle, backgroundColor: '#f0f0f0' }} styles={{ body: { padding: '10px 20px 15px' } }}>
                  <Paragraph style={{margin: 0, fontWeight: 'bold', fontSize: '16px'}}>{result.final_answer}</Paragraph>
                </Card>
              </Space>
            )}
          </Spin>
        </div>
      </div>
    </AntApp>
  )
}

export default App
