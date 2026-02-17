import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json

# --- CONFIGURATION SÉCURISÉE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante dans les secrets.")

# Utilisation du modèle (Gemini 2.0 Flash est le standard actuel pour la rapidité)
model = genai.GenerativeModel('gemini-2.5-flash')

def generer_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # --- CHARGEMENT DES POLICES ---
    # Note : Il est CRUCIAL de déclarer les deux avec le même nom de famille 'DejaVu'
    # mais en spécifiant le style ('B' pour le Bold)
    try:
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
        font_name = 'DejaVu'
        euro = "€"
    except Exception as e:
        st.warning(f"Erreur chargement polices : {e}. Repli sur Arial.")
        font_name = 'Arial'
        euro = "EUR"

    # --- EN-TÊTE ---
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 10, f"FACTURE : {data.get('nom_magasin', 'COMMERCE')}", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 8, f"Date : {data.get('date', 'N/A')}", 0, 1, 'R')
    pdf.ln(5)

    # --- TABLEAU DYNAMIQUE (TEXTE LONG) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_name, 'B', 11)
    
    w_nom = 130
    w_prix = 40
    
    pdf.cell(w_nom, 10, " Description", 1, 0, 'L', True)
    pdf.cell(w_prix, 10, "Prix TTC", 1, 1, 'C', True)

    pdf.set_font(font_name, '', 10)
    
    for art in data.get('articles', []):
        nom_txt = str(art.get('nom', 'Article'))
        prix_val = f"{float(art.get('prix_unitaire_ttc', 0)):.2f} {euro}"
        
        # --- GESTION DU TEXTE LONG ---
        # On mémorise la position de départ
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # MultiCell permet le retour à la ligne automatique
        pdf.multi_cell(w_nom, 8, nom_txt, border=1, align='L')
        
        # On calcule la hauteur que MultiCell a utilisé
        y_end = pdf.get_y()
        h_cell = y_end - y_start
        
        # On se replace à droite de la cellule de nom pour dessiner le prix
        pdf.set_xy(x_start + w_nom, y_start)
        pdf.cell(w_prix, h_cell, prix_val, border=1, ln=1, align='R')

    # --- TOTAUX ---
    pdf.ln(10)
    # On recalcule les totaux en Python pour éviter les erreurs d'IA
    total_ttc = sum(float(a.get('prix_unitaire_ttc', 0)) for a in data.get('articles', []))
    taux_tva = float(data.get('taux_tva', 20))
    total_ht = total_ttc / (1 + taux_tva/100)
    total_tva = total_ttc - total_ht

    pdf.set_font(font_name, '', 11)
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

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Facture Pro", page_icon="🧾")
st.title("🧾 Scanner de Ticket vers Facture")

img_file = st.file_uploader("Téléchargez le ticket", type=['jpg', 'jpeg', 'png'])

if img_file:
    st.image(img_file, width=300)
    
    if st.button("Analyser et Générer le PDF"):
        with st.spinner("Extraction des données..."):
            try:
                img_bytes = img_file.getvalue()
                
                # On force Gemini à ne répondre qu'en JSON
                prompt = """Analyse ce ticket et retourne UNIQUEMENT un JSON avec :
                "nom_magasin", "date", "taux_tva" (float), 
                "articles" (liste avec "nom" et "prix_unitaire_ttc")."""
                
                response = model.generate_content([
                    prompt, 
                    {"mime_type": img_file.type, "data": img_bytes}
                ])
                
                # Extraction du JSON propre
                raw_text = response.text.replace('```json', '').replace('```', '').strip()
                data_json = json.loads(raw_text)
                
                # Génération du PDF binaire
                pdf_output = generer_pdf(data_json)
                
                st.success("Analyse terminée !")
                st.download_button(
                    label="📥 Télécharger la Facture PDF",
                    data=pdf_output,
                    file_name="facture_pro.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Erreur : {e}")
