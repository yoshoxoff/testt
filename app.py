import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json

# --- CONFIGURATION API ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante dans les secrets.")

# Configuration pour Gemini 2.5
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash', # Ajuste le nom exact si nécessaire selon ta version
    generation_config={"response_mime_type": "application/json"}
)

def generer_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # --- GESTION DES POLICES (SÉCURISÉE) ---
    font_name = 'Arial'
    euro = "EUR"
    
    try:
        # On essaie d'ajouter les deux variantes séparément
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
        font_name = 'DejaVu'
        euro = "€"
    except Exception as e:
        st.warning(f"Police DejaVu non trouvée, repli sur Arial. Erreur : {e}")
        # Arial est standard, pas besoin de add_font

    # --- EN-TÊTE ---
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 10, f"FACTURE : {data.get('nom_magasin', 'COMMERCE')}", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 6, f"Date : {data.get('date', 'N/A')}", 0, 1, 'R')
    pdf.ln(10)

    # --- TABLEAU DYNAMIQUE (TEXTE LONG) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_name, 'B', 11)
    
    col_nom = 130
    col_prix = 40
    
    pdf.cell(col_nom, 10, " Description", 1, 0, 'L', True)
    pdf.cell(col_prix, 10, "Total TTC", 1, 1, 'C', True)

    pdf.set_font(font_name, '', 10)
    
    for art in data.get('articles', []):
        nom_texte = str(art['nom'])
        prix_texte = f"{float(art['prix_unitaire_ttc']):.2f} {euro}"
        
        # Calcul de la hauteur nécessaire pour le texte long
        # On utilise multi_cell en mode "simulation" pour calculer la hauteur
        start_y = pdf.get_y()
        pdf.multi_cell(col_nom, 8, nom_texte, border=1, align='L')
        end_y = pdf.get_y()
        h_cell = end_y - start_y
        
        # On se replace pour dessiner la case du prix à côté avec la même hauteur
        pdf.set_xy(10 + col_nom, start_y)
        pdf.cell(col_prix, h_cell, prix_texte, border=1, ln=1, align='R')

    # --- TOTAUX ---
    pdf.ln(5)
    total_ttc = sum(float(a['prix_unitaire_ttc']) for a in data['articles'])
    taux_tva = float(data.get('taux_tva', 20))
    total_ht = total_ttc / (1 + taux_tva/100)
    total_tva = total_ttc - total_ht

    pdf.set_x(110)
    pdf.cell(40, 8, "TOTAL HT", 0, 0, 'L')
    pdf.cell(40, 8, f"{total_ht:.2f} {euro}", 1, 1, 'R')
    
    pdf.set_x(110)
    pdf.cell(40, 8, f"TVA ({taux_tva}%)", 0, 0, 'L')
    pdf.cell(40, 8, f"{total_tva:.2f} {euro}", 1, 1, 'R')
    
    pdf.set_font(font_name, 'B', 12)
    pdf.set_x(110)
    pdf.cell(40, 10, "TOTAL TTC", 0, 0, 'L')
    pdf.cell(40, 10, f"{total_ttc:.2f} {euro}", 1, 1, 'R', fill=True)

    return pdf.output(dest='S')

# --- STREAMLIT UI ---
st.title("🧾 Scanner Facture Pro 2.5")

file = st.file_uploader("Upload ticket", type=['png', 'jpg', 'jpeg'])

if file:
    img_bytes = file.getvalue()
    if st.button("Générer Facture"):
        with st.spinner("Analyse par Gemini 2.5..."):
            try:
                prompt = "Extrais les données de ce ticket au format JSON : nom_magasin, date, taux_tva (float), articles (liste avec nom et prix_unitaire_ttc)."
                
                response = model.generate_content([
                    prompt,
                    {"mime_type": file.type, "data": img_bytes}
                ])
                
                data = json.loads(response.text)
                pdf_bytes = generer_pdf(data)
                
                st.download_button("📥 Télécharger PDF", pdf_bytes, "facture.pdf", "application/pdf")
            except Exception as e:
                st.error(f"Erreur : {e}")
