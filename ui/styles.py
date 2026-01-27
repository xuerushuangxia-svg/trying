"""
UI 样式定义
"""

CUSTOM_CSS = """
<style>
.report-card { 
    background: white; 
    padding: 25px; 
    border-radius: 12px; 
    border-left: 8px solid #ccc; 
    margin-bottom: 20px; 
    box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
}
.status-red { 
    border-left-color: #ef4444; 
    background: #fef2f2; 
}
.status-yellow { 
    border-left-color: #f59e0b; 
    background: #fffbeb; 
}
.status-green { 
    border-left-color: #10b981; 
    background: #f0fdf4; 
}
.risk-title { 
    font-size: 20px; 
    font-weight: bold; 
    color: #1e293b; 
    margin-bottom: 10px; 
}
.detail-text { 
    font-size: 15px; 
    color: #475569; 
    line-height: 1.8; 
}
.logic-tag { 
    background: #e2e8f0; 
    padding: 2px 8px; 
    border-radius: 4px; 
    font-size: 12px; 
    font-weight: bold; 
}
</style>
"""
