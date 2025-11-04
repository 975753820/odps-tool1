import streamlit as st
import pandas as pd
import math
import tempfile
import os
from odps import ODPS

# 页面配置
st.set_page_config(
    page_title="ODPS数据导出工具",
    page_icon="📊",
    layout="centered"
)

st.title("📊 ODPS数据导出工具")
st.markdown("轻松将ODPS数据导出为Excel文件")

def get_odps_connection(access_id, access_key, project, endpoint):
    """根据用户输入的凭据获取ODPS连接"""
    try:
        if not access_id or not access_key:
            st.error("请输入完整的ODPS凭据")
            return None
            
        return ODPS(access_id, access_key, project, endpoint)
    except Exception as e:
        st.error(f"ODPS连接失败: {e}")
        return None

def safe_odps_query(table_name, access_id, access_key, project, endpoint, max_rows=100000):
    """安全执行ODPS查询"""
    try:
        o = get_odps_connection(access_id, access_key, project, endpoint)
        if not o:
            return None
            
        # 安全限制
        safe_max_rows = min(max_rows, 500000)
        sql = f"SELECT * FROM {table_name} LIMIT {safe_max_rows}"
        
        with st.spinner(f"正在查询数据，最多{safe_max_rows}行..."):
            with o.execute_sql(sql).open_reader() as reader:
                return reader.to_pandas()
                
    except Exception as e:
        st.error(f"查询失败: {e}")
        return None

# 侧边栏 - ODPS配置
with st.sidebar:
    st.header("🔐 ODPS配置")
    
    access_id = st.text_input(
        "Access ID",
        placeholder="输入您的Access ID",
        type="password",
        help="ODPS访问密钥ID"
    )
    
    access_key = st.text_input(
        "Access Key", 
        placeholder="输入您的Access Key",
        type="password",
        help="ODPS访问密钥"
    )
    
    project = st.text_input(
        "Project",
        value="HSAY_ETL",
        help="ODPS项目名称"
    )
    
    endpoint = st.text_input(
        "Endpoint",
        value="http://service.cn-shanghai.maxcompute.aliyun.com/api",
        help="ODPS服务端点"
    )
    
    st.markdown("---")
    st.info("""
    **配置说明：**
    - 首次使用需要输入ODPS凭据
    - 凭据仅在当前会话有效
    - 不会保存到服务器
    """)

# 主界面 - 数据导出
st.subheader("数据导出")

# 检查凭据是否已输入
if not access_id or not access_key:
    st.warning("⚠️ 请在左侧输入ODPS凭据以开始使用")
    st.stop()

with st.form("export_form"):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        table_name = st.text_input(
            "📋 ODPS表名 *",
            placeholder="例如: hsay_etl_dev.order_table",
            help="格式: 项目名.表名"
        )
    
    with col2:
        max_rows = st.selectbox(
            "📊 最大行数",
            [10000, 50000, 100000, 200000, 500000],
            index=2,
            help="为保障系统性能设置的行数限制"
        )
    
    submitted = st.form_submit_button(
        "🚀 开始导出", 
        use_container_width=True,
        type="primary"
    )

if submitted:
    if not table_name:
        st.error("请输入ODPS表名")
    else:
        df = safe_odps_query(table_name, access_id, access_key, project, endpoint, max_rows)
        
        if df is not None and not df.empty:
            # 显示数据预览
            st.success(f"✅ 查询成功！共找到 {len(df):,} 行数据")
            
            with st.expander("📈 数据预览", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
            
            # 生成Excel文件
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("正在生成Excel文件...")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                # 分sheet写入
                sheet_num = math.ceil(len(df) / 800000)
                
                with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                    for i in range(sheet_num):
                        status_text.text(f"正在写入第 {i+1}/{sheet_num} 个Sheet...")
                        progress_bar.progress((i + 1) / sheet_num)
                        
                        start_idx = i * 800000
                        end_idx = min((i + 1) * 800000, len(df))
                        df.iloc[start_idx:end_idx].to_excel(
                            writer, 
                            sheet_name=f'数据_{i+1}', 
                            index=False
                        )
                
                with open(tmp_file.name, 'rb') as f:
                    excel_data = f.read()
            
            # 准备下载
            filename = f"{table_name.split('.')[-1]}.xlsx"
            
            status_text.success("✅ 文件生成完成！")
            progress_bar.progress(1.0)
            
            st.download_button(
                label="📥 点击下载Excel文件",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
            
            # 清理临时文件
            try:
                os.unlink(tmp_file.name)
            except:
                pass
        else:
            st.error("查询失败或返回空数据，请检查：")
            st.info("""
            1. 表名是否正确
            2. ODPS凭据是否有权限
            3. 网络连接是否正常
            """)

# 使用说明
with st.expander("❓ 使用帮助", expanded=True):
    st.markdown("""
    ### 使用方法：
    1. **左侧输入ODPS凭据**（首次使用需要）
    2. **输入表名**：格式为 `项目名.表名`
    3. **选择行数**：设置最大导出行数
    4. **点击导出**：系统自动查询并生成Excel
    5. **下载文件**：点击下载按钮保存
    
    ### 示例表名：
    - `hsay_etl_dev.order_table`
    - `hsay_etl_dev.user_info` 
    - `hsay_etl_dev.sales_data`
    
    ### 安全说明：
    - ODPS凭据仅在当前浏览器会话有效
    - 页面刷新后需要重新输入
    - 凭据不会发送到其他服务器
    """)

# 连接状态显示
with st.sidebar:
    st.markdown("---")
    if access_id and access_key:
        st.success("✅ 凭据已输入")
    else:
        st.error("❌ 凭据未输入")

st.markdown("---")
st.caption("ODPS数据导出工具 | 安全的前台凭据输入")
