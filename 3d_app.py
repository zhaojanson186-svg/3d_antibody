import streamlit as st
import requests
from stmol import showmol
import py3Dmol

# ==========================================
# 1. 网页全局设置
# ==========================================
st.set_page_config(page_title="🧊 抗体 3D 建模实验室", page_icon="🧬", layout="wide")

st.title("🧊 纯净版：抗体 3D 建模与 VH-VL 拼接终端")
st.markdown("💡 **独立运行，极致轻量**。专注处理 Fv 区的三维构象预测。支持单独折叠重/轻链，或通过 (G4S)3 柔性 Linker 自动拼接预测 scFv 复合体。")

# ==========================================
# 2. 核心功能区：输入与参数设置
# ==========================================
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    vh_seq = st.text_area("🔵 输入重链 (VH) 氨基酸序列:", height=150, placeholder="例如: EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAK...")

with col2:
    vl_seq = st.text_area("🟢 输入轻链 (VL) 氨基酸序列:", height=150, placeholder="例如: DIQMTQSPSSLSASVGDRVTITCRASQGIRNDLGWYQQKPGKAPKRLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCLQHNSYP...")

st.markdown("### ⚙️ 建模策略配置")
mode = st.radio(
    "选择预测模式:", 
    ["🧬 智能拼接 scFv (VH + (G4S)3 Linker + VL) - 推荐用于排查配对", 
     "🔵 仅预测 VH 单链结构", 
     "🟢 仅预测 VL 单链结构"]
)

# 可选：手动输入高危位点进行高亮
ptm_input = st.text_input("🚨 (可选) 红色预警位点标记:", placeholder="输入需要高亮为红球的残基位置，用逗号隔开，如: 54, 102")

# ==========================================
# 3. 建模引擎与渲染
# ==========================================
if st.button("🚀 呼叫云端算力，启动原子级建模", type="primary"):
    
    # 序列清洗
    clean_vh = "".join(vh_seq.split()).upper()
    clean_vl = "".join(vl_seq.split()).upper()
    linker = "GGGGSGGGGSGGGGS"
    target_seq = ""
    
    # 根据模式组装最终序列
    if "scFv" in mode:
        if not clean_vh or not clean_vl:
            st.error("❌ 拼接模式需要同时输入 VH 和 VL 序列！")
            st.stop()
        target_seq = clean_vh + linker + clean_vl
    elif "VH" in mode:
        target_seq = clean_vh
        if not target_seq:
            st.error("❌ VH 序列不能为空！")
            st.stop()
    else:
        target_seq = clean_vl
        if not target_seq:
            st.error("❌ VL 序列不能为空！")
            st.stop()

    # 处理 PTM 高亮位点
    ptm_sites = []
    if ptm_input.strip():
        try:
            ptm_sites = [int(x.strip()) for x in ptm_input.split(",") if x.strip().isdigit()]
        except:
            st.warning("⚠️ 位点格式解析错误，已忽略高亮请求。请确保输入的是纯数字加逗号。")

    # 开始请求 ESMFold
    with st.spinner(f"🚀 正在折叠包含 {len(target_seq)} 个氨基酸的构象，这通常需要 10-30 秒..."):
        url = "https://api.esmatlas.com/foldSequence/v1/pdb/"
        
        try:
            # 延长超时时间到 30 秒，专门应对长序列的 scFv
            response = requests.post(url, data=target_seq, timeout=30)
            
            if response.status_code == 200:
                pdb_data = response.text
                st.success("✅ 云端建模成功！")
                
                # --- 渲染 3D 视图 ---
                view = py3Dmol.view(width=800, height=500)
                view.addModel(pdb_data, 'pdb')
                
                # 默认设为彩虹色
                view.setStyle({'cartoon': {'color': 'spectrum'}})
                
                # 如果有预警位点，加上红色球体
                if ptm_sites:
                    for site in ptm_sites:
                        view.addStyle({'resi': str(site)}, {'cartoon': {'color': 'spectrum'}, 'sphere': {'color': 'red', 'radius': 1.5}})
                        
                view.zoomTo()
                
                # 左右分栏展示结果和下载按钮
                r_col1, r_col2 = st.columns([3, 1])
                with r_col1:
                    showmol(view, height=500, width=800)
                with r_col2:
                    st.markdown("#### 📥 模型下载")
                    st.write("将该 PDB 文件导入 PyMOL 等桌面端软件进行高精度分析。")
                    st.download_button(
                        label="下载 .pdb 结构文件",
                        data=pdb_data,
                        file_name="Antibody_3D_Model.pdb",
                        mime="protein/x-pdb",
                        type="primary"
                    )
                    
                    if "scFv" in mode:
                        st.info(f"💡 **序列长度说明:**\nVH: {len(clean_vh)} AA\nLinker: 15 AA\nVL: {len(clean_vl)} AA\n总计: {len(target_seq)} AA")
                        
            else:
                st.error(f"❌ 建模失败。云端引擎返回状态码: {response.status_code}")
                if len(target_seq) > 400:
                    st.warning("⚠️ 您的序列超过 400 个氨基酸，超出了免费版 ESMFold 接口的算力极限，请缩短序列。")
                    
        except requests.exceptions.Timeout:
            st.error("⏳ 请求超时！这通常是因为您输入的序列过长 (scFv)，导致云端 GPU 计算时间超过了 30 秒。请稍后再试，或尝试只预测单链。")
        except Exception as e:
            st.error(f"❌ 发生未知错误: {e}")
