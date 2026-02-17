import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json

# --- CONFIGURATION SÉCURISÉE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante. Configurez GEMINI_API_KEY dans les secrets.")

# Modèle Gemini 2.5 Flash
model = genai.GenerativeModel('gemini-2.5-flash') 

def generer_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. FIX POLICE : On tente l'Unicode, sinon on bascule proprement sur Arial
    font_name = 'Arial'
    euro = "EUR"
    try:
        # On force uni=True pour fpdf
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
        font_name = 'DejaVu'
        euro = "€"
    except:
        font_name = 'Arial'
        euro = "EUR"

    # En-tête
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 10, f"FACTURE : {data.get('nom_magasin', 'MAGASIN')}", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 10, f"Date: {data.get('date', 'N/A')}", 0, 1)
    pdf.ln(5)

    # 2. TABLEAU AVEC GESTION TEXTE LONG (MultiCell)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_name, 'B', 11)
    
    # Largeurs colonnes
    w_nom = 130
    w_prix = 40

    pdf.cell(w_nom, 10, " Description", 1, 0, 'L', True)
    pdf.cell(w_prix, 10, "Prix TTC", 1, 1, 'R', True)

    pdf.set_font(font_name, '', 10)
    
    for art in data.get('articles', []):
        nom = str(art.get('nom', 'Article'))
        prix = f"{float(art.get('prix_unitaire_ttc', 0)):.2f} {euro}"
        
        # On calcule la hauteur nécessaire pour le nom
        # MultiCell permet au texte de passer à la ligne si c'est trop long
        x_before = pdf.get_x()
        y_before = pdf.get_y()
        
        pdf.multi_cell(w_nom, 8, nom, border=1)
        y_after = pdf.get_y()
        h_cell = y_after - y_before
        
        # On se remet à côté pour le prix
        pdf.set_xy(x_before + w_nom, y_before)
        pdf.cell(w_prix, h_cell, prix, border=1, ln=1, align='R')

    # 3. TOTAUX (Recalculés pour la sécurité)
    pdf.ln(5)
    total_ttc = sum(float(a.get('prix_unitaire_ttc', 0)) for a in data.get('articles', []))
    taux_tva = float(data.get('taux_tva', 20))
    total_ht = total_ttc / (1 + taux_tva/100)
    total_tva = total_ttc - total_ht

    pdf.set_font(font_name, '', 11)
    pdf.set_x(110)
    pdf.cell(30, 10, "TOTAL HT", 0, 0, 'L')
    pdf.cell(40, 10, f"{total_ht:.2f} {euro}", 1, 1, 'R')
    
    pdf.set_x(110)
    pdf.cell(30, 10, f"TVA ({taux_tva}%)", 0, 0, 'L')
    pdf.cell(40, 10, f"{total_tva:.2f} {euro}", 1, 1, 'R')
    
    pdf.set_font(font_name, 'B', 12)
    pdf.set_x(110)
    pdf.cell(30, 12, "TOTAL TTC", 0, 0, 'L')
    pdf.cell(40, 12, f"{total_ttc:.2f} {euro}", 1, 1, 'R', fill=True)

    # Important: renvoyer le binaire propre
    return pdf.output(dest='S')

# --- INTERFACE STREAMLIT ---
st.title("🧾 Scanner Facture Gemini 2.5")

file = st.file_uploader("Ticket", type=['jpg', 'jpeg', 'png'])

if file:
    img_bytes = file.getvalue()
    st.image(img_bytes, width=250)

    if st.button("Générer la vraie facture"):
        with st.spinner("Analyse..."):
            try:
                # Prompt spécifique pour forcer un JSON propre
                prompt = """Analyse ce ticket. Retourne STRICTEMENT ce JSON :
                {
                  "nom_magasin": "string",
                  "date": "string",
                  "taux_tva": float,
                  "articles": [{"nom": "string", "prix_unitaire_ttc": float}]
                }"""
                
                response = model.generate_content([
                    prompt, 
                    {"mime_type": file.type, "data": img_bytes}
                ])
                
                # Nettoyage robuste du JSON
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                resultats = json.loads(clean_json)
                
                # Génération
                pdf_bytes = generer_pdf(resultats)
                
                st.success("Fait !")
                st.download_button("📥 Télécharger PDF", pdf_bytes, "facture.pdf", "application/pdf")
                
            except Exception as e:
                st.error(f"Erreur : {e}")
