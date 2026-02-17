import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json

# --- CONFIGURATION SÉCURISÉE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante. Configurez GEMINI_API_KEY dans les secrets.")

# Utilisation du mode JSON natif de Gemini
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

class FacturePDF(FPDF):
    def header(self):
        # On peut ajouter un logo ici si besoin
        self.set_font('DejaVu', 'B', 15)
        self.cell(0, 10, 'FACTURE PROFESSIONNELLE', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generer_pdf(data):
    pdf = FacturePDF()
    pdf.add_page()
    
    # CHARGEMENT POLICE
    try:
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
        font_main = 'DejaVu'
        euro = "€"
    except:
        font_main = 'Arial'
        euro = "EUR"

    # --- INFOS MAGASIN ---
    pdf.set_font(font_main, 'B', 12)
    pdf.cell(0, 8, data.get('nom_magasin', 'MAGASIN INCONNU').upper(), 0, 1)
    pdf.set_font(font_main, '', 10)
    pdf.cell(0, 5, f"Date: {data.get('date', 'N/A')}", 0, 1)
    pdf.ln(10)

    # --- TABLEAU (GESTION DU TEXTE LONG) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_main, 'B', 10)
    
    # Largeurs des colonnes
    col_nom = 130
    col_prix = 50
    
    pdf.cell(col_nom, 10, " Description de l'article", 1, 0, 'L', True)
    pdf.cell(col_prix, 10, "Total TTC", 1, 1, 'C', True)

    pdf.set_font(font_main, '', 10)
    
    for art in data.get('articles', []):
        nom_art = str(art['nom'])
        prix_art = f"{art['prix_unitaire_ttc']:.2f} {euro}"
        
        # Calcul de la hauteur nécessaire pour le texte (MultiCell)
        # On utilise multi_cell pour que le texte long passe à la ligne
        x_before = pdf.get_x()
        y_before = pdf.get_y()
        
        # Colonne Nom (MultiCell gère le texte long)
        pdf.multi_cell(col_nom, 8, nom_art, border=1, align='L')
        y_after = pdf.get_y()
        h_cell = y_after - y_before # Hauteur dynamique
        
        # Colonne Prix (On se replace à côté de la cellule Nom)
        pdf.set_xy(x_before + col_nom, y_before)
        pdf.cell(col_prix, h_cell, prix_art, border=1, ln=1, align='R')

    pdf.ln(5)

    # --- RÉCAPITULATIF FINANCIER ---
    # On pousse les totaux vers la droite
    pdf.set_x(120)
    pdf.set_font(font_main, '', 10)
    
    # Calculs de sécurité (au cas où l'IA se trompe)
    total_ttc = sum(a['prix_unitaire_ttc'] for a in data['articles'])
    taux = data.get('taux_tva', 20)
    total_ht = total_ttc / (1 + taux/100)
    total_tva = total_ttc - total_ht

    pdf.cell(35, 8, "Total HT", 0, 0, 'L')
    pdf.cell(35, 8, f"{total_ht:.2f} {euro}", 1, 1, 'R')
    
    pdf.set_x(120)
    pdf.cell(35, 8, f"TVA ({taux}%)", 0, 0, 'L')
    pdf.cell(35, 8, f"{total_tva:.2f} {euro}", 1, 1, 'R')
    
    pdf.set_x(120)
    pdf.set_font(font_main, 'B', 11)
    pdf.cell(35, 10, "TOTAL TTC", 0, 0, 'L')
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(35, 10, f"{total_ttc:.2f} {euro}", 1, 1, 'R', True)

    return pdf.output(dest='S')

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Scanner Facture Pro", page_icon="🧾")
st.title("🧾 Extracteur de Factures")

fichier_image = st.file_uploader("Upload du ticket", type=['jpg', 'jpeg', 'png'])

if fichier_image:
    st.image(fichier_image, width=300)
    
    if st.button("🚀 Générer la Facture"):
        with st.spinner("Analyse précise en cours..."):
            try:
                img_bytes = fichier_image.getvalue()
                
                prompt = """Analyse ce ticket. Extraie chaque article individuellement. 
                Si un nom d'article est long, garde-le en entier. 
                Retourne le JSON suivant :
                {
                  "nom_magasin": "string",
                  "date": "string",
                  "taux_tva": float,
                  "articles": [{"nom": "string", "prix_unitaire_ttc": float}]
                }"""
                
                response = model.generate_content([
                    prompt, 
                    {"mime_type": fichier_image.type, "data": img_bytes}
                ])
                
                # Le mode JSON de Gemini 2.0 garantit une réponse JSON valide sans texte autour
                resultats_ia = json.loads(response.text)
                
                # Génération
                pdf_output = generer_pdf(resultats_ia)
                
                st.success("Facture prête !")
                st.download_button(
                    label="📥 Télécharger le PDF",
                    data=pdf_output,
                    file_name=f"facture_{resultats_ia.get('nom_magasin', 'scan')}.pdf",
                    mime="application/pdf"
                )
                
            except Exception as e:
                st.error(f"Erreur : {e}")
