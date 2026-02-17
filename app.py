import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json

# --- CONFIGURATION SÉCURISÉE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante. Configurez GEMINI_API_KEY dans les secrets.")

model = genai.GenerativeModel('gemini-2.5-flash')

# --- FONCTION GENERATION PDF ---
def generer_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    try:
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
        font_name = 'DejaVu'
        use_chr128 = False
    except:
        font_name = 'Arial'
        use_chr128 = True
    
    # En-tête
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 10, f"FACTURE : {data['nom_magasin']}", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 10, f"Date: {data['date']}", 0, 1)
    pdf.ln(5)

    # Tableau - En-tête
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(130, 10, "Article", 1, 0, 'L', True)
    pdf.cell(40, 10, "Prix TTC", 1, 1, 'R', True)

    euro = chr(128) if use_chr128 else "€"
    pdf.set_font(font_name, '', 12)

    # --- BOUCLE ARTICLES AVEC RETOUR À LA LIGNE ---
    for art in data['articles']:
        # On mémorise la position X et Y avant d'écrire l'article
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # MultiCell pour le nom (largeur 130)
        # Ça revient à la ligne tout seul si c'est trop long
        pdf.multi_cell(130, 10, art['nom'], border=1)
        
        # On calcule la position Y après le texte pour connaître la hauteur
        y_end = pdf.get_y()
        h_cell = y_end - y_start
        
        # On se replace à droite de la cellule qu'on vient de faire pour mettre le prix
        pdf.set_xy(x_start + 130, y_start)
        
        # Cellule du prix avec la même hauteur (h_cell) pour que les bordures s'alignent
        pdf.cell(40, h_cell, f"{art['prix_unitaire_ttc']:.2f} {euro}", 1, 1, 'R')

    pdf.ln(5)
    
    # Totaux
    pdf.set_font(font_name, '', 12)
    pdf.cell(130, 10, "TOTAL HT", 0, 0, 'R')
    pdf.cell(40, 10, f"{data['total_ht']:.2f} {euro}", 1, 1, 'R')
    
    pdf.cell(130, 10, f"TVA ({data['taux_tva']}%)", 0, 0, 'R')
    pdf.cell(40, 10, f"{data['total_tva']:.2f} {euro}", 1, 1, 'R')
    
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(130, 10, "TOTAL TTC", 0, 0, 'R')
    pdf.cell(40, 10, f"{data['total_ttc']:.2f} {euro}", 1, 1, 'R')
    
    # Sortie binaire
    return pdf.output(dest='S')

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Scanner de Tickets Pro", page_icon="🧾")
st.title("🧾 Convertisseur Ticket en Facture")

fichier_image = st.file_uploader("Choisissez une photo de ticket (JPG, PNG)", type=['jpg', 'jpeg', 'png'])

if fichier_image is not None:
    st.image(fichier_image, caption="Ticket téléchargé", width=300)
    
    if st.button("Analyser et Générer la Facture"):
        with st.spinner("L'IA analyse les montants et la TVA..."):
            try:
                img_bytes = fichier_image.getvalue()
                prompt = """Analyse ce ticket de caisse. 
                Retourne UNIQUEMENT un objet JSON avec cette structure :
                {
                  "nom_magasin": "string",
                  "date": "string",
                  "taux_tva": float,
                  "articles": [{"nom": "string", "prix_unitaire_ttc": float}],
                  "total_ht": float,
                  "total_tva": float,
                  "total_ttc": float
                }"""
                
                response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
                texte_reponse = response.text.replace('```json', '').replace('```', '').strip()
                resultats_ia = json.loads(texte_reponse)
                
                pdf_output = generer_pdf(resultats_ia)
                
                st.success("Analyse terminée !")
                st.download_button(
                    label="📥 Télécharger la Facture PDF",
                    data=pdf_output,
                    file_name="facture_automatique.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {e}")
