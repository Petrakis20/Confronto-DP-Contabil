
        # ========== CONFRONTO INSS ==========
        if 'confronto_inss' in st.session_state and impostos_geral:
            st.markdown("---")
            st.header("📊 Confronto INSS")
            st.info("📌 Comparação entre INSS Total Líquido (Resumo Geral) e Soma dos Eventos INSS de todos os resumos")
            
            confronto_inss = st.session_state['confronto_inss']
            
            # Cards principais
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">💰 INSS Resumo Geral</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Total Líquido</p>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(confronto_inss['inss_resumo_geral'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">📝 Soma Eventos INSS</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Adicionais - Descontos</p>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(confronto_inss['inss_liquido_eventos'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                diferenca = confronto_inss['inss_diferenca']
                status = confronto_inss['status']
                cor_status = '#28a745' if status == '✅ OK' else '#dc3545'
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">⚖️ Diferença</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Geral - Eventos</p>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(diferenca)}
                    </p>
                    <p style="background: {cor_status}; color: white; padding: 5px; border-radius: 5px; font-size: 0.9em; margin-top: 10px;">
                        {status}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # Detalhamento por categoria em expander
            with st.expander("📊 Ver Detalhamento por Categoria"):
                if confronto_inss['inss_eventos_por_categoria']:
                    st.subheader("Eventos INSS por Categoria")
                    
                    # Totais gerais
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Adicionais", money(confronto_inss['inss_total_adicionais']))
                    with col2:
                        st.metric("Total Descontos", money(confronto_inss['inss_total_descontos']))
                    
                    st.markdown("---")
                    
                    # Detalhes por categoria
                    for categoria, valores in confronto_inss['inss_eventos_por_categoria'].items():
                        st.markdown(f"### {categoria}")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Adicionais", money(valores['adicionais']))
                        with col2:
                            st.metric("Descontos", money(valores['descontos']))
                        with col3:
                            st.metric("Líquido", money(valores['liquido']))
                        st.markdown("")
                else:
                    st.info("Nenhum evento INSS encontrado nos resumos")

