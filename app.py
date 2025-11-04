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

def get_odps_connection():
    """安全获取ODPS连接"""
    try:
        access_id = os.getenv('ODPS_ACCESS_ID')
        access_key = os.getenv('ODPS_ACCESS_KEY')
        project = os.getenv('ODPS_PROJECT', 'HSAY_ETL')
        endpoint = os.getenv('ODPS_ENDPOINT', 'http://service.cn-shanghai.maxcompute.aliyun.com/api')
        
        if not access_id or not access_key:
            st.error("系统配置异常，请联系管理员")
            return None
            
        return ODPS(access_id, access_key, project, endpoint)
    except Exception as e:
        st.error(f"连接失败: {e}")
        return None

def safe_odps_query(table_name, max_rows=100000):
    """安全执行ODPS查询"""
    try:
        o = get_odps_connection()
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

# 主界面
st.subheader("数据导出")

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
            [10000, 50000, 100000, 200000],
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
        df = safe_odps_query(table_name, max_rows)
        
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

# 使用说明
with st.expander("❓ 使用帮助", expanded=True):
    st.markdown("""
    ### 使用方法：
    1. **输入表名**：格式为 `项目名.表名`
    2. **选择行数**：设置最大导出行数
    3. **点击导出**：系统自动查询并生成Excel
    4. **下载文件**：点击下载按钮保存
    
    ### 示例表名：
    - `hsay_etl_dev.order_table`
    - `hsay_etl_dev.user_info`
    - `hsay_etl_dev.sales_data`
    """)

st.markdown("---")
st.caption("ODPS数据导出工具")
