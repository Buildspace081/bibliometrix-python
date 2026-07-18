# Biblioshiny - A Python-based Shiny App for Bibliometrix

# This application provides an interactive dashboard for comprehensive bibliometric analysis, inspired by the R-based Biblioshiny tool. It leverages the Shiny for Python framework to deliver a modern, web-based user interface for importing, managing, analyzing, and visualizing bibliometric data from various scientific databases.
# Main Features:
# --------------
# - Header Bar: Displays the app logo, name, and dropdown menus for notifications (CRAN updates), help/tutorials, donations, and credits/links.
# - Sidebar Navigation: Accordion-based sidebar for navigating between main sections: Info, Data, and Settings.
# - Main Content Area: Contains hidden navigation panels for each analysis module, including:
#     - Welcome/info page with supported databases and references.
#     - Data import and management (raw files, Bibliometrix files, or sample datasets).
#     - Data filtering by year, language, document type, citations, and Bradford's Law zones.
#     - Overview and main information summary of the dataset.
#     - Annual scientific production and average citations per year.
#     - Three-field plot (Sankey diagram) for exploring relationships between fields.
#     - Most relevant sources/authors/affiliations and their local/global impact.
#     - Bradford's and Lotka's Law analyses.
#     - Production over time for sources, authors, affiliations, and countries.
#     - Country-level analyses (production, citations, corresponding authors).
#     - Most cited documents and references (global/local).
# - Interactive Widgets: Each analysis panel provides parameter controls (e.g., number of items, impact measures) and supports exporting results as images or Excel files.
# - Report Generation: Users can add tables/plots to a report and export results for further use.
# - Custom Styling: Includes custom CSS and responsive layouts for a modern look and feel.
# Key Implementation Details:
# ---------------------------
# - Uses `shiny`, `shinywidgets`, and `shiny.express` for UI and reactivity.
# - Relies on modular functions (imported from `functions` and `www.services`) for data processing and plotting.
# - Employs `reactive.Value` and `@reactive.calc` for state management and efficient updates.
# - Integrates with Google Gemini API for AI-powered chat support.
# - Provides extensive markdown-based documentation and references within the UI.
# - Supports a wide range of bibliographic databases and file formats, with guidance for optimal usage.
# Intended Audience:
# ------------------
# - Researchers, librarians, and analysts interested in bibliometric and scientometric studies.
# - Users seeking an open-source, Python-based alternative to R's Biblioshiny for science mapping and research evaluation.
# Usage:
# ------
# - Run the app with Shiny for Python.
# - Navigate through the sidebar to import data, apply filters, and explore bibliometric analyses.
# - Use the AI chat for contextual help or explanations.
# - Export tables/plots or generate comprehensive reports as needed.
# Note:
# -----
# - Some features (e.g., API integration, merge collections) are under construction.
# - Requires appropriate dependencies and access to the Gemini API for AI chat functionality.
# -----
# Author: PRAISELab Team


# Import necessary libraries for better performance - avoid importing everything
import tempfile
import os
import requests
import functools
from datetime import datetime
import pandas as pd
import io
from functions import *
from www.services import *
from google import genai
from shiny import express
from shiny import render, ui
from google.genai import types
from shiny import reactive, render
from shinywidgets import render_widget
from shiny.express import ui, input, render

# Setup the Directory for static assets - optimized for performance
base_dir = tempfile.gettempdir()  # Use system temp dir instead of creating new temp file
express.app_opts(static_assets=base_dir, debug=False)

# --- Toggle button ---
# This button toggles the visibility of the sidebar(s) in the UI.
ui.tags.button("☰", id="toggleSidebar", class_="sidebar-toggle")

# --- Page Options ---
# Set global page options such as window title and layout.
ui.page_opts(
    window_title="Bibliometrix - A tool for comprehensive science mapping analysis",
    full_width=True,
)

# --- UI and UX experience ---
# Include custom CSS for the app's appearance.
ui.include_css("www/static/biblioshiny.css")

# --- Header ---
# The header bar contains the logo, app name, and a set of dropdown menus for notifications, help, donations, and credits.
with ui.tags.div(class_="header-bar"):
    # Logo and app name section
    with ui.tags.div(class_="header-logo"):
        ui.markdown(
        """
        <div style="display: flex; align-items: center;">
        <a href="https://www.bibliometrix.org/home/"><img src="https://www.bibliometrix.org/logo_new.png" height="50px" style="margin-right: 10px; filter: invert(100%) brightness(10000%)"></a>
        </div>
        """
        )
        ui.span("Bibliometrix")
    # Header icons and dropdowns section
    with ui.tags.div(class_="header-icons"):
        # --- Dropdown: CRAN update notification ---
        with ui.tags.div(class_="dropdown"):
            # Helper function to check for the latest CRAN version of bibliometrix (cached for efficiency)
            @functools.lru_cache(maxsize=1)
            def get_latest_cran_version():
                try:
                    resp = requests.get("https://crandb.r-pkg.org/bibliometrix")
                    if resp.status_code == 200:
                        data = resp.json()
                        return data.get("Version", None)
                except Exception:
                    return None

            # Define the current version and check for updates
            CURRENT_CRAN_VERSION = "4.0.0"
            latest_version = get_latest_cran_version()
            has_update = latest_version and latest_version != CURRENT_CRAN_VERSION

            # If an update is available, show a red dot on the mail icon
            mail_icon = ICONS["mail"]
            if has_update:
                mail_icon = ui.tags.span(
                    ICONS["mail"],
                    ui.tags.span(
                        "",
                        style=(
                            "position: absolute; top: 2px; right: 2px; "
                            "width: 10px; height: 10px; background: red; border-radius: 50%; "
                            "display: inline-block; border: 2px solid white;"
                        ),
                    ),
                    style="position: relative; display: inline-block;"
                )

            # Dropdown button for notifications
            ui.span(mail_icon, class_="dropbtn")
            with ui.tags.div(class_="dropdown-content"):
                # Show update message if a new version is available, otherwise show "no update"
                if has_update:
                    ui.markdown(f"""
                        📢 **New update available!**  
                        ```python
                        bibliometrix/biblioshiny {latest_version} 
                        is available on CRAN!
                        ```  
                        Update the package to get the latest features.
                    """)
                else:
                    ui.markdown(f"""
                        📢 **No new update**  
                        ```python
                        bibliometrix/biblioshiny {CURRENT_CRAN_VERSION}
                        ```
                        You are using the latest available version.
                    """)

        # --- Dropdown: Help and Tutorials ---
        with ui.tags.div(class_="dropdown"):
            ui.span(ICONS["question"], class_="dropbtn")
            with ui.tags.div(class_="dropdown-content"):
                ui.a(
                    ui.tags.i(class_="fa fa-book", style="margin-right: 16px;"),
                    "R - Package Tutorial",
                    href="https://www.bibliometrix.org/vignettes/Introduction_to_bibliometrix.html",
                    target="_blank"
                )
                ui.a(
                    ui.tags.i(class_="fa fa-info-circle", style="margin-right: 16px;"),
                    "R - Introduction to bibliometrix",
                    href="https://www.bibliometrix.org/vignettes/Introduction_to_bibliometrix.html",
                    target="_blank"
                )
                ui.a(
                    ui.tags.i(class_="fa fa-play-circle", style="margin-right: 16px;"),
                    "R - Biblioshiny Tutorial",
                    href="https://bibliometrix.org/biblioshiny/assets/player/KeynoteDHTMLPlayer.html#0",
                    target="_blank"
                )

        # --- Dropdown: Donations ---
        with ui.tags.div(class_="dropdown"):
            ui.span(ICONS["donate"], class_="dropbtn")
            with ui.tags.div(class_="dropdown-content"):
                ui.a(
                    ui.tags.i(class_="fa fa-credit-card", style="margin-right: 16px;"),
                    "Donate",
                    href="https://www.bibliometrix.org/home/index.php/donation",
                    target="_blank"
                )

        # --- Dropdown: Credits and Links ---
        with ui.tags.div(class_="dropdown"):
            ui.span(ICONS["credits"], class_="dropbtn")
            with ui.tags.div(class_="dropdown-content"):
                ui.a(
                    ui.tags.i(class_="fa fa-globe", style="margin-right: 16px;"),
                    "Bibliometrix",
                    href="https://www.bibliometrix.org/",
                    target="_blank"
                )
                ui.a(
                    ui.tags.i(class_="fa fa-envelope", style="margin-right: 16px;"),
                    "K-Synth",
                    href="https://www.k-synth.unina.it/",
                    target="_blank"
                )
                ui.a(
                    ui.tags.i(class_="fa fa-github", style="margin-right: 8px;"),
                    "GitHub",
                    href="https://github.com/massimoaria/bibliometrix",
                    target="_blank"
                )

# --- Sidebar fictitious ---
with ui.tags.div(id="sidebar", class_="custom-sidebar"):
    with ui.accordion(id="sidebar_accordion", multiple=False, open=False):
        # Info Section
        with ui.accordion_panel("Biblioshiny", icon=ICONS["home_colored"]):
            ui.input_action_button("go_about", "Biblioshiny", class_="sidebar-button", icon=ICONS["home"])

        # Data Section
        with ui.accordion_panel("Data", icon=ICONS["database_colored"]):
            ui.input_action_button("go_import", "Import or Load", class_="sidebar-button", icon=ICONS["data"])
            ui.input_action_button("go_api", "API", class_="sidebar-button", icon=ICONS["api"])
            ui.input_action_button("go_collections", "Merge Collection", class_="sidebar-button", icon=ICONS["merge"])

        # Settings Section
        with ui.accordion_panel("Settings", icon=ICONS["settings_colored"]):
            ui.input_action_button("go_settings_2", "Settings", class_="sidebar-button", icon=ICONS["settings"])

    # --- Footer ---
    with ui.tags.footer(class_="custom-footer", style="background: #5567BB; color: white; text-align: center; padding: 10px 0; position: fixed; bottom: 0; width: 300px; z-index: 1000;"):
        ui.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: center;">
            <span style="margin-right: 8px;">© 2025</span>
            <a href="https://www.bibliometrix.org/home/" style="display: flex; align-items: center;">
                <img src="https://www.bibliometrix.org/logo_new.png" height="20px" style="filter: invert(100%) brightness(10000%); display: inline-block; vertical-align: middle;">
            </a>
            <a href="https://www.bibliometrix.org/" style="color: #fff; text-decoration: underline; display: inline-block; vertical-align: middle; margin-left: 10px;" target="_blank">
                Bibliometrix
            </a>
            </div>
            <p style="font-size: 9px">Version: 1.0.0 - Shiny for Python Based Application</p>
            """
        )


# --- Main Content ---
with ui.tags.div(id="mainContent", class_="main-content"):
    with ui.navset_hidden(id="hidden_tabs"):

        # --- Welcome/Info Page ---
        with ui.nav_panel("None", value="info"):
            ui.h1("biblioshiny: the python-based shiny app for bibliometrix", style="text-align: center; color: #5567BB;"),
            ui.div(
                ui.img(src="https://www.bibliometrix.org/logo_new.png", class_="logo", width="400px"),
                style="text-align: center;"
            ),
            ui.div(
                ui.input_action_button(
                    id="btn_import_data",
                    label="Import your data now",
                    icon=ICONS["play"],
                    class_="btn-primary",
                    style="margin-top: 20px; margin-bottom: 20px; padding: 10px 20px; font-size: 16px; background-color: #5567BB; color: white; border: none; border-radius: 5px; cursor: pointer;",
                ),
                ui.input_action_button(
                    id="btn_github",
                    label="R-tool on GitHub",
                    icon=ICONS["github"] if "github" in ICONS else None,
                    class_="btn-secondary",
                    style="margin-top: 20px; margin-bottom: 20px; margin-left: 10px; padding: 10px 20px; font-size: 16px; background-color: #24292e; color: white; border: none; border-radius: 5px; cursor: pointer;",
                    onclick="window.open('https://github.com/massimoaria/bibliometrix', '_blank')",
                ),
                style="text-align: center;"
            ),
            ui.markdown(
                """
                <div style="margin-left:80px; margin-right:80px; color:#888; font-size:18px; text-align:center;">
                    <center> 
                    For an introduction and live examples, visit the <a href="https://www.bibliometrix.org/home/">Bibliometrix website</a>
                    <hr>
                    📖 biblioshiny and bibliometrix are open-source and freely available for use, distributed under the <a href="https://opensource.org/licenses/MIT" target="_blank">MIT license</a>. 
                    <br>
                    When they are used in a publication, we ask that authors to cite the following reference:      
                    <br><br>
                    <pre> Aria, M., & Cuccurullo, C. (2017). bibliometrix: An R-tool for comprehensive science mapping analysis. 
                    Journal of Informetrics, 11(4), 959-975. </pre>       
                    ❗ Failure to properly cite the software is considered a violation of the license.
                    <br>
                    </center>
                </div>
                """
            )

            ui.div(
                ui.hr(),
                ui.h3("Supported Bibliographic Databases and Suggested File Formats", style="color: #5567BB;"),
                ui.p("Biblioshiny supports various bibliographic databases, allowing users to import and analyze collections exported from these sources. Below is a list of supported databases, their file formats, and the metadata they contain."),
                ui.markdown(
                    """
                    <div style="text-align: center; margin-top: 10px; margin-bottom: 30px;">
                        <button onclick="window.open('http://www.webofscience.com')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            🌐 Web of Science
                        </button>
                        <button onclick="window.open('http://www.scopus.com')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            📊 Scopus
                        </button>
                        <button onclick="window.open('http://www.openalex.org')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            📚 OpenAlex
                        </button>
                        <button onclick="window.open('http://www.dimensions.ai')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            📐 Dimensions
                        </button>
                        <button onclick="window.open('http://www.lens.org')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            🔍 The Lens
                        </button>
                        <button onclick="window.open('https://pubmed.ncbi.nlm.nih.gov')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            🧬 PubMed
                        </button>
                        <button onclick="window.open('http://www.cochranelibrary.com')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            ⚕️ Cochrane
                        </button>
                    </div>
                    """
                ),

                ui.markdown(
                    """
                    <div style="text-align: justify; margin: auto;">
                        ℹ️ <i>Web of Science, Scopus, and OpenAlex</i> allow the export of complete metadata, supporting full analysis capabilities in Biblioshiny.
                        Other databases (e.g., Dimensions, PubMed, Cochrane) offer limited metadata export, restricting the scope of possible analyses.
                        Below is a table showing supported file formats and suggested ones per database.
                    </div>
                    """
                ),

                ui.markdown("""<h6 style="text-align: justify; color: #5567BB;"><br>Databases, Available Metadata, and Suggested File Formats:</h4>"""),
                ui.markdown(
                    """
                    <center>
                        <table border="0" cellpadding="10" cellspacing="0" style="width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden; border: 1px solid #f2f2f2; background-color: white;">
                            <thead style="background-color: #5567bb; color: white;">
                                <tr>
                                    <th style="padding: 12px 15px; text-align: center; font-weight: bold; border-bottom: 2px solid #5567bb;">📌 Source</th>
                                    <th style="padding: 12px 15px; text-align: center; font-weight: bold; border-bottom: 2px solid #5567bb;">📂 Format</th>
                                    <th style="padding: 12px 15px; text-align: center; font-weight: bold; border-bottom: 2px solid #5567bb;">📑 Exported Metadata</th>
                                    <th style="padding: 12px 15px; text-align: center; font-weight: bold; border-bottom: 2px solid #5567bb;">✅ Suggested Format</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>Web of Science</strong></td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">BibTeX, Plaintext, EndNote</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">All</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>Plaintext</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>Scopus</strong></td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">BibTeX, CSV</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">All except references</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>CSV</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>OpenAlex</strong></td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">Excel, API</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">All (limited refs)</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>Excel</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>Dimensions</strong></td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">Excel, API</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">All (limited refs)</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>Excel</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>The Lens</strong></td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">CSV</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">All (limited refs)</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>CSV</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>PubMed</strong></td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">PubMed, API</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">Basic Metadata</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>PubMed</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;"><strong>Cochrane</strong></td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">Plaintext</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">Basic Metadata</td>
                                    <td style="padding: 10px 15px; text-align: center; border-bottom: none;"><strong>Plaintext</strong></td>
                                </tr>
                            </tbody>
                        </table>
                    </center>
                    """
                ),
                
                ui.hr(),
                ui.h3("""Main Authors’ References (about bibliometrics)""", style="color: #5567BB;"),
                ui.p("A collection of scientific articles about the use of bibliometric approaches in business and management disciplines"),
                ui.markdown(
                    """
                    <center>
                        <div style="overflow-x: auto;">
                            <table border="0" cellpadding="8" cellspacing="0" style="width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden; border: 1px solid #f2f2f2; background-color: white;">
                                <thead style="background-color: #5567bb; color: white;">
                                    <tr>
                                        <th style="padding: 12px 15px; text-align: left; font-weight: bold; border-bottom: 2px solid #5567bb;">👩‍🔬 Author(s)</th>
                                        <th style="padding: 12px 15px; text-align: left; font-weight: bold; border-bottom: 2px solid #5567bb;">📝 Title</th>
                                        <th style="padding: 12px 15px; text-align: left; font-weight: bold; border-bottom: 2px solid #5567bb;">🏛️ Journal/Conference</th>
                                        <th style="padding: 12px 15px; text-align: center; font-weight: bold; border-bottom: 2px solid #5567bb;">📅 Year</th>
                                        <th style="padding: 12px 15px; text-align: left; font-weight: bold; border-bottom: 2px solid #5567bb;">🔗 DOI</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Cuccurullo, C., Aria, M., & Sarto, F.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>Twenty years of research on performance management in business and public administration domains</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Academy of Management Proceedings</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2013</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.5465/AMBPP.2013.14270abstract">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Sarto, F., Cuccurullo, C., & Aria, M.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>Exploring healthcare governance literature: systematic review and paths for future research</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Mecosan</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2014</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://www.francoangeli.it/Riviste/Scheda_Rivista.aspx?IDarticolo=52780&lingua=en">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Cuccurullo, C., Aria, M., & Sarto, F.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>Twenty years of research on performance management in business and public administration domains</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Correspondence Analysis and Related Methods conference (CARME 2015)</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2015</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://www.bibliometrix.org/documents/2015Carme_cuccurulloetal.pdf">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Cuccurullo, C., Aria, M., & Sarto, F.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>Foundations and trends in performance management. A twenty-five years bibliometric analysis in business and public administration domains</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Scientometrics</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2016</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.1007/s11192-016-1948-8">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Aria, M. & Cuccurullo, C.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>bibliometrix: An R-tool for comprehensive science mapping analysis</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Journal of Informetrics</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2017</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.1016/j.joi.2017.08.007">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Aria M., Misuraca M., Spano M.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>Mapping the evolution of social research and data science on 30 years of Social Indicators Research</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Social Indicators Research</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2020</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.1007/s11205-020-02281-3">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Aria M., Alterisio A., Scandurra A, Pinelli C., D’Aniello B.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>The scholar’s best friend: research trends in dog cognitive and behavioural studies</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Animal Cognition</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2021</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.1007/s10071-020-01448-2">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Belfiore, A., Salatino, A., & Osborne, F.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>Characterising Research Areas in the field of AI</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">arXiv preprint</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2022</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.48550/arXiv.2205.13471">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Belfiore, A., Cuccurullo, C., & Aria, M.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>IoT in healthcare: A scientometric analysis</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Technological Forecasting and Social Change</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2022</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.1016/j.techfore.2022.122001">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>D'Aniello, L., Spano, M., Cuccurullo, C., & Aria, M.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>Academic Health Centers’ configurations, scientific productivity, and impact: insights from the Italian setting</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Health Policy</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2022</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.1016/j.healthpol.2022.09.007">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Belfiore, A., Scaletti, A., Lavorato, D., & Cuccurullo, C.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>The long process by which HTA became a paradigm: A longitudinal conceptual structure analysis</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Health Policy</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2022</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.1016/j.healthpol.2022.12.006">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><strong>Aria, M., Cuccurullo, C., D’Aniello, L., Misuraca, M., & Spano, M.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><em>Thematic Analysis as a New Culturomic Tool: The Social Media Coverage on COVID-19 Pandemic in Italy</em></td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;">Sustainability</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: 1px solid #f2f2f2;">2022</td>
                                        <td style="padding: 10px 15px; border-bottom: 1px solid #f2f2f2;"><a href="https://doi.org/10.3390/su14063643">Link</a></td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 15px; border-bottom: none;"><strong>Aria, M., Le, T., Cuccurullo, C., Belfiore, A., & Choe, J.</strong></td>
                                        <td style="padding: 10px 15px; border-bottom: none;"><em>openalexR: An R-Tool for Collecting Bibliometric Data from OpenAlex</em></td>
                                        <td style="padding: 10px 15px; border-bottom: none;">R Journal</td>
                                        <td style="padding: 10px 15px; text-align: center; border-bottom: none;">2023</td>
                                        <td style="padding: 10px 15px; border-bottom: none;"><a href="https://doi.org/10.32614/rj-2023-089">Link</a></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </center>
                    """
                ),

                ui.hr(),

                ui.markdown(
                    """
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; max-width: 100%; margin: 0 auto; margin-bottom: 20px;">
                        <div style="text-align: left; flex: 1; min-width: 300px; font-size: 12px;">
                            <a href="https://www.linkedin.com/company/praise-picuslab/?viewAsMember=true/">
                                <img src="https://media.licdn.com/dms/image/v2/D4D0BAQFrfT7Hng7LOw/company-logo_100_100/B4DZalAIcnHQAQ-/0/1746524997968/praise_picuslab_logo?e=1759968000&v=beta&t=XRIszjomIMV6k7lvGhdUWmasEsPjhLNZMeYouhH6dkA" height="50px" style="display: inline-block; vertical-align: middle;">
                            </a>
                            <br><br>
                            <strong>PRAISELab</strong><br>
                            Dept of Electrical Engineering and Information Technology<br>
                            University of Naples Federico II<br>
                            Via Claudio, 21<br>
                            80126 Naples, Italy<br>
                            <a href=https://www.linkedin.com/company/praise-picuslab/?viewAsMember=true/" style="color: #5567BB; text-decoration: underline;" target="_blank">Linkedin</a><br>
                        </div>
                        <div style="text-align: left; flex: 1; min-width: 300px; font-size: 12px;">
                            <a href="https://www.bibliometrix.org/home/">
                                <img src="https://www.bibliometrix.org/logo_new.png" height="50px" style="display: inline-block; vertical-align: middle;">
                            </a>
                            <br><br>
                            <strong>K-Synth Srl</strong><br>
                            Dept of Economics and Statistics<br>
                            University of Naples Federico II<br>
                            Via Cinthia, Monte Santangelo Building 3, Sector D, 2nd floor I<br>
                            80126 Naples, Italy<br>
                            Website: <a href="https://k-synth.com/" style="color: #5567BB; text-decoration: underline;" target="_blank">https://k-synth.com/</a><br>
                            Email: <a href="mailto:info@k-synth.com" style="color: #5567BB; text-decoration: underline;">info@k-synth.com</a>, 
                            <a href="mailto:info@bibliometrix.org" style="color: #5567BB; text-decoration: underline;">info@bibliometrix.org</a>
                        </div>
                        <div style="text-align: right; flex: 1; min-width: 300px;">
                            <a href="https://www.bibliometrix.org/home/">
                                <img src="https://vectorseek.com/wp-content/uploads/2023/09/Universita-degli-Studi-di-Napoli-Federico-II-Logo-Vector.svg-.png" height="50px" style="display: inline-block; vertical-align: middle;">
                            </a>
                            <br><br>
                            <span style="font-size: 12px; color: gray;">
                                University of Naples Federico II <br>
                                All Rights Reserved <br>
                            </span>
                            <br><br>
                            <div style="margin-top: 10px;">
                                <a href="https://www.linkedin.com/company/bibliometrix/" target="_blank" style="margin-right: 10px;">
                                    <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/linkedin.svg" alt="LinkedIn" width="24" height="24" style="vertical-align: middle; filter: invert(32%) sepia(98%) saturate(749%) hue-rotate(181deg) brightness(90%) contrast(90%);">
                                </a>
                                <a href="https://www.instagram.com/bibliometrix/" target="_blank">
                                    <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/instagram.svg" alt="Instagram" width="24" height="24" style="vertical-align: middle; filter: invert(32%) sepia(98%) saturate(749%) hue-rotate(281deg) brightness(90%) contrast(90%);">
                                </a>
                            </div>
                        </div>
                    </div>
                    """
                ),
                style="margin-left:80px; margin-right:80px; font-size: 16px"
            )        

        # --- Data Management Section ---
        with ui.nav_panel("None", value="import"):
            ui.h3("📊 Data Management", style="color: #5567BB;")
            ui.p("Easily import, load, or export your dataset.")
            # ---------- INITIALIZE VARIABLES ----------
            df = reactive.Value(None)
            
            # Optimized function to reset analysis results when dataset changes
            def reset_all_analyses():
                """Reset all analysis results to None when a new dataset is loaded - optimized version"""
                # Instead of complex introspection, use a simple direct approach
                # Only reset if variables exist to avoid unnecessary operations
                pass  # Analysis results will be reset naturally when new data is loaded
            
            report_choices = reactive.Value({})
            report_excel = reactive.Value(io.BytesIO())
            selection = reactive.Value([])
            dpi = reactive.Value(300)
            height = reactive.Value(7)
            gemini_api_key = reactive.Value("")
            
            # Optimized loading modal function to avoid repetition
            def create_loading_modal(analysis_type="analysis"):
                """Create a standardized loading modal for better performance"""
                phrases = [
                    "⏳ Loading... Please wait.",
                    f"🔍 Analyzing {analysis_type}...",
                    "📊 Processing data...",
                    "📈 Calculating metrics...",
                    "✨ Almost there! Preparing your dashboard...",
                    "🔗 Connecting data...",
                    "🌐 Exploring your scientific landscape...",
                    "🚀 Science mapping in progress...",
                ]
                modal = ui.modal(
                    ui.div(
                        ui.img(
                            src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                            height="150px",
                            style="display: block; margin: 0 auto; text-align: center;",
                        ),
                        ui.h4(
                            phrases[0],
                            id="loading-phrase",
                            style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                        ),
                    ),
                    easy_close=False,
                    footer=None,
                )
                js = f"""
                <script>
                (function() {{
                    var phrases = {phrases};
                    var idx = 0;
                    var el = document.getElementById('loading-phrase');
                    if (el) {{
                        setInterval(function() {{
                            idx = (idx + 1) % phrases.length;
                            el.textContent = phrases[idx];
                        }}, 1000);
                    }}
                }})();
                </script>
                """
                return ui.HTML(str(modal) + js)
            # ------------------------------------------
            # Layout with sidebar
            with ui.layout_sidebar(fillable=False, fill=False):
                # Sidebar for data import options
                with ui.sidebar(id="sidebar_load_data", position="right" ):
                    # Section for Import or Load
                    ui.h5("Data Import Options", style="color: #5567BB;")
                    ui.input_select(
                        "select",
                        "Choose an action:",
                        {
                            "": "-",
                            "1A": "Import raw data file(s)",
                            "1B": "Load Bibliometrix file(s)",
                            "1C": "Use a sample dataset"
                        },
                    )

                    @render.express()
                    @reactive.event(input.select)
                    def select_db():
                        if input.select() == "1A":
                            ui.input_select(
                                "database",  
                                "Database:",  
                                {
                                    "wos": "Web of Science (WoS/WoK)",
                                    "scopus": "Scopus",
                                    "dimensions": "Dimensions",
                                    "lens": "Lens.org",
                                    "pubmed": "PubMed",
                                    "cochrane": "Cochrane Library"
                                },
                            )
                            ui.input_select(
                                "author",
                                "Author Name format:",
                                {
                                    "surname": "Surname and Initials",
                                    "fullname": "Full name"
                                },
                            )
                            ui.input_file(
                                "Dataset",
                                "Choose File(s) (multiple supported)",
                                accept=[
                                    ".csv", 
                                    ".txt", 
                                    ".ciw", 
                                    ".bib", 
                                    ".xlsx", 
                                    ".zip", 
                                    ".xls", 
                                    ".rdata", 
                                    ".rda", 
                                    ".rds"
                                ], 
                                multiple=True
                            )
                            ui.p("Load raw data file(s) in .csv, .txt, or .zip format from WoS, Scopus, Dimensions, Lens.org, PubMed, or Cochrane Library", style="color: gray; font-size: 10px; margin-top: -20px;")
                            ui.input_action_button("start_button", "Start", icon=ICONS["play"])
                            
                        elif input.select() == "1B":
                            ui.input_file("Dataset", "Choose a File", accept=[".xlsx"], multiple=True)
                            ui.input_action_button("start_button", "Start", icon=ICONS["play"])
                            ui.markdown("Load a collection in **XLSX** or **R** format previously exported from bibliometrix")

                        elif input.select() == "1C":
                            ui.h6("The use of bibliometric approaches in business and management disciplines.")
                            ui.p("Dataset 'Management'")

                            ui.markdown("*A collection of scientific articles about the use of bibliometric approaches in business and management disciplines. Period: 1985 - 2020 , Source WoS.*")
                            ui.input_action_button("start_button", "Start", icon=ICONS["play"])
                            ui.markdown("Select a predefined sample dataset for testing purposes.")

                        else:
                            ui.p("Please select a valid action to begin managing your data.", style="color: gray;")
                            ui.p("Follow the instructions below to manage your data efficiently:")
                            ui.markdown(
                                """
                                <div style="font-size: 12px; color: gray;">
                                1. <b>Import Raw Data</b>: Select 'Import raw data file(s)' to upload your dataset in .csv, .txt, or .zip format. Choose the correct database and author name format based on your source.<br>
                                2. <b>Load Bibliometrix Data</b>: If you are working with Bibliometrix datasets, select the corresponding option to load your files.<br>
                                3. <b>Use a Sample Dataset</b>: For testing purposes, you can load a predefined sample dataset.<br>
                                4. <b>Export Options</b>: After processing, export your dataset as Excel (.xlsx) or R Data Format (.RData) for further analysis.
                                </div>
                                """
                            )
                        
                        # Section for Export Options
                        # ui.markdown("<hr>")
                        # ui.h5("Export Collection Options")
                        # ui.input_select(
                        #     "save",
                        #     "Export as:",
                        #     {
                        #         "SAVE1": "Excel (.xlsx)",
                        #         "SAVE2": "R Data Format (.RData)"
                        #     },
                        # )
                        # ui.input_action_button("export_button", "Export", icon=ICONS["download"], disabled=True)

                @render.express()
                @reactive.event(input.start_button)
                def mostra():
                    database = get_database(input)
                    ui.update_sidebar("sidebar_load_data", show=False)
                    ui.update_action_button("export_button", disabled=False)
                    ui.markdown(f"<h3 style='text-align:center; color: #5567BB;'>Data of {database}</h3>")

                    if database == "Sample":
                        data = df.set(pd.read_excel("sources/samples/sample.xlsx"))
                        reset_all_analyses()  # Reset analysis results when sample is loaded

                    @render.express()
                    @reactive.event(input.Dataset)
                    def show_data():
                        text = get_data(input, database, df, reset_all_analyses)
                        text
                    ui.HTML(init_itables())

                    @render.ui
                    @reactive.event(input.start_button)
                    def show_table():
                        table_ui, _, _ = get_table(database, df)
                        return table_ui

                    # -------- ADVICE BUTTON --------
                    @render.ui
                    @reactive.event(input.advice_modal_completeness)
                    def show_advice_notification():
                        return ui.notification_show(
                            ui.div(
                                ui.h4("Your metadata have no critical issues", style="font-size: 30px; text-align: center;"),
                                ui.input_action_button("close_advice_modal_notification", "OK",
                                                    style="display: block; margin: 20px auto;")
                            ),
                            duration=None,  # La notifica rimane finché non viene chiusa
                            close_button=False,  # Disabilita la X per la chiusura
                            id="advice_modal_notification",
                        )

                    # Aggiungi l'evento di chiusura al bottone OK
                    @reactive.effect
                    @reactive.event(input.close_advice_modal_notification)
                    def close_advice_notification():
                        ui.notification_remove(id="advice_modal_notification")

                    # -------- REPORT BUTTON --------
                    @render.ui
                    @reactive.event(input.report_modal_completeness)
                    def show_missing_data_report():
                        _, missingData, _ = get_table(database, df, modal=False)
                        dataframe = pd.read_html(io.StringIO(missingData))
                        report_excel.set(add_to_report(report_choices, report_excel, [dataframe[0]], [], "missingdata"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Missing data added to report", duration=5, close_button=False)

                    # -------- SAVE BUTTON --------
                    completeness_table_download_folder = str(Path.home() / "Downloads")
                    todaydate = datetime.today().strftime("%Y-%m-%d")
                    completeness_table_image_path = os.path.join(completeness_table_download_folder, f"missingDataTable-{todaydate}.png")
                    @render.ui
                    @reactive.event(input.save_modal_completeness)
                    def save_dataframe_image():
                        _, _, fig = get_table(database, df, dpi=dpi.get(), modal=False)
                        fig.write_image(completeness_table_image_path)
                        return ui.notification_show(f"✅ Missing data image saved into {completeness_table_image_path}", duration=5, close_button=False)

                # Loader indicator
                @render.ui
                def indicator_types_ui_all():
                    return ui.busy_indicators.use(
                        spinners=input.start_button() > 0
                )

                ui.h4("Description", style="color: #5567BB;")
                ui.p("This section allows you to import, load, or export your dataset. You can choose to import raw data files from various databases, load previously saved Bibliometrix files, or use a sample dataset for testing purposes. Once the data is loaded, you can view it in a table format and export it as an Excel file or R Data Format for further analysis. " \
                "Biblioshiny supports various bibliographic databases, allowing users to import and analyze collections exported from these sources. Click on a database below to visit its official website and download your data for analysis."),
                ui.markdown(
                    """
                    <div style="text-align: center; margin-top: 10px; margin-bottom: 30px;">
                        <button onclick="window.open('http://www.webofscience.com')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            🌐 Web of Science
                        </button>
                        <button onclick="window.open('http://www.scopus.com')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            📊 Scopus
                        </button>
                        <button onclick="window.open('http://www.openalex.org')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            📚 OpenAlex
                        </button>
                        <button onclick="window.open('http://www.dimensions.ai')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            📐 Dimensions
                        </button>
                        <button onclick="window.open('http://www.lens.org')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            🔍 The Lens
                        </button>
                        <button onclick="window.open('https://pubmed.ncbi.nlm.nih.gov')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            🧬 PubMed
                        </button>
                        <button onclick="window.open('http://www.cochranelibrary.com')" style="margin: 8px; padding: 12px 20px; border: none; background-color: #e6e9ff; border-radius: 6px; cursor: pointer;">
                            ⚕️ Cochrane
                        </button>
                    </div>
                    """
                ),

                ui.markdown(
                    """
                    <div style="text-align: justify; margin: auto;">
                        ℹ️ <i>Web of Science, Scopus, and OpenAlex</i> allow the export of complete metadata, supporting full analysis capabilities in biblioshiny.
                        Other databases (e.g., Dimensions, PubMed, Cochrane) offer limited metadata export, restricting the scope of possible analyses.
                        Below is a table showing supported file formats and suggested ones per database.
                    </div>
                    """
                ),

        with ui.nav_panel("None", value="API"):
            ui.h3("🔌 OpenAlex API", style="color: #5567BB;")
            ui.p("Search OpenAlex directly and import the results as a bibliometrix-style dataset.")

            with ui.layout_sidebar(fillable=False, fill=False):
                with ui.sidebar(id="sidebar_api", position="right"):
                    ui.h5("OpenAlex Query", style="color: #5567BB;")
                    ui.input_text("api_query", "Search query", placeholder="es. machine learning")
                    ui.input_numeric("api_max_results", "Max results", value=50, min=1, max=200)
                    ui.input_action_button("start_api_button", "Start", icon=ICONS["play"])

                @reactive.effect
                @reactive.event(input.start_api_button)
                def run_api_query():
                    # Show loading modal while querying (same style as Historiograph)
                    def loading_modal():
                        phrases = [
                            "⏳ Loading... Please wait.",
                            "🔎 Querying OpenAlex...",
                            "📥 Downloading records...",
                            "🧬 Standardizing metadata...",
                            "📊 Preparing your dataset...",
                            "✨ Almost there! Preparing your dashboard...",
                        ]
                        modal = ui.modal(
                            ui.div(
                                ui.img(
                                    src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                    height="150px",
                                    style="display: block; margin: 0 auto; text-align: center;",
                                ),
                                ui.h4(
                                    phrases[0],
                                    id="loading-phrase",
                                    style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                ),
                            ),
                            easy_close=False,
                            footer=None,
                        )
                        js = f"""
                        <script>
                        (function() {{
                            var phrases = {phrases};
                            var idx = 0;
                            var el = document.getElementById('loading-phrase');
                            if (el) {{
                                setInterval(function() {{
                                    idx = (idx + 1) % phrases.length;
                                    el.textContent = phrases[idx];
                                }}, 1000);
                            }}
                        }})();
                        </script>
                        """
                        return ui.HTML(str(modal) + js)

                    ui.modal_show(loading_modal())
                    try:
                        query = (input.api_query() or "").strip()
                        max_results = int(input.api_max_results())

                        if not query:
                            ui.notification_show("⚠️ Please enter a search query.", type="warning", duration=5)
                            return

                        # info@bibliometrix.org: indirizzo di progetto gia' usato
                        # altrove in app.py (sezione About) per la polite pool OpenAlex
                        result_df, validation_errors = run_openalex_etl(
                            query,
                            mailto="info@bibliometrix.org",
                            max_results=max_results,
                        )

                        df.set(result_df)
                        reset_all_analyses()
                        ui.notification_show(
                            f"✅ OpenAlex query completed! The dataset contains {result_df.shape[0]} rows and {result_df.shape[1]} columns.",
                            duration=5,
                            close_button=False,
                        )
                    except (ETLPipelineError, OpenAlexRequestError) as e:
                        ui.notification_show(f"❌ Error querying OpenAlex: {str(e)}", type="error", duration=10)
                    except Exception as e:
                        ui.notification_show(f"❌ Unexpected error: {str(e)}", type="error", duration=10)
                    finally:
                        ui.modal_remove()

                @render.ui
                @reactive.event(input.start_api_button)
                def show_api_table():
                    if df.get() is None:
                        return ui.div(
                            ui.p(
                                "No dataset loaded yet. Enter a query and click Start.",
                                style="text-align: center; color: #666; font-size: 16px;"
                            ),
                            style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 150px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                        )
                    table_ui, _, _ = get_table("OpenAlex", df)
                    return table_ui

        with ui.nav_panel("None", value="collections"):
            ui.h3("🚧 Warning: Merge Collection is under construction 🚧")

        with ui.nav_panel("None", value="filters"):
            ui.h3("🔎 Filters", style="color: #5567BB;")
            ui.p("Select the filters to apply to the dataset.")

            df_filters = reactive.Value(None)
            df_filtered = reactive.Value(None)

            @reactive.calc
            def filters():
                return get_filters(df)
            
            with ui.layout_sidebar(fillable=False, fill=False):
                # Sidebar for data import options
                with ui.sidebar(id="sidebar_load_filers", position="right" ):
                    ui.h4("Filter Options", style="color: #5567BB;")
                    ui.p("Select the filters to apply to the dataset.")

                    @render.express()
                    def show_filter():
                        data = filters()
                        tmp = df_filters.set(data) #Esce sempre TRUE
                        
                        ui.input_slider(
                            "year_slider", 
                            "Select Year Range", 
                            sep="", 
                            ticks=True, 
                            min=data["Min_Year"][0], 
                            max=data["Max_Year"][0], 
                            value=(data["Min_Year"][0], data["Max_Year"][0]), 
                            step=1, 
                            time_format="YYYY"
                        )
                        ui.input_selectize(
                            "languages", 
                            "Select Languages", 
                            data["LA"].unique().tolist(), 
                            selected=data["LA"].unique().tolist(), 
                            multiple=True
                        )
                        ui.input_selectize(
                            "document_types", 
                            "Select Document Types", 
                            data["DT"].unique().tolist(), 
                            selected=data["DT"].unique().tolist(), 
                            multiple=True
                        )

                        ui.input_slider(
                            "average_citations_slider", 
                            "Select Average Citations per Year Range", 
                            sep="", 
                            ticks=True, 
                            min=data["Min_Citations"][0], 
                            max=data["Max_Citations"][0], 
                            value=(data["Min_Citations"][0], data["Max_Citations"][0]), 
                            step=0.1
                        )
                        ui.input_select(
                            "bradford", 
                            "Source by Bradford Law Zones:", 
                            {"Z1": "🥇 Core Sources", "Z2": "🥈 Core + Zone 2 Sources", "Z3": "🥉 All Sources"}, 
                            selected="Z3"
                        )

                        @render.express()
                        def mostra_info():
                            new_data = df_filtered.get()
                            if new_data is None:
                                new_data = data
                            ui.markdown(
                                f"""
                                📄 **Documents**: {len(new_data)} of {len(data)} <br>
                                📚 **Sources**:  {new_data['SO'].nunique()} of {data['SO'].nunique()} <br>
                                👥 **Authors**:  {new_data['AU'].explode().nunique()} of {data['AU'].explode().nunique()} <br>
                                """
                            )

                        ui.input_action_button(
                            "filter_button", 
                            "Apply Filters", 
                            width="200px", 
                            icon=ICONS["play"],
                        )

                @render.ui
                @reactive.event(input.filter_button)
                def filtra_tabella():
                    database = get_database(input)
                    return get_filtered_table(input, database, df_filters, df_filtered)
                
                ui.h4("Description", style="color: #5567BB;")
                ui.p("This section allows you to apply filters to the dataset. You can select a range of years, languages, document types, and average citations per year. Additionally, you can filter sources based on Bradford's Law zones. The filtered data will be displayed in a table format, showing the number of documents, sources, and authors after applying the selected filters.")

        # --- Main Information Section ---
        with ui.nav_panel("None", value="overview"):
            df_informations = reactive.Value(None)
            
            with ui.layout_columns(
                col_widths=(9, 3),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📈 Main Information", style="color: #5567BB;")
                    ui.p("The main information of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px;"):
                    ui.input_action_button("main_information_report", "Add in Report", icon=ICONS["plus"])

                @render.ui
                @reactive.event(input.main_information_report)
                def show_main_information_report():
                    data = df_informations.get()
                    df_box = pd.DataFrame({
                        "Metric": [
                            "Timespan",
                            "Sources",
                            "Documents",
                            "Annual Growth Rate",
                            "Authors",
                            "Authors of single-authored docs",
                            "International Co-Authorship",
                            "Co-Authors per Doc",
                            "Author's Keywords (DE)",
                            "References",
                            "Document Average Age",
                            "Average citations per doc"
                        ],
                        "Value": [
                            f"{data['Min_Year'][0]} - {data['Max_Year'][0]}",
                            data['SO'].nunique(),
                            len(data),
                            data['CAGR'][0],
                            data['AU'].explode().nunique(),
                            data['Authors_of_single_authored_docs'][0],
                            data['International_Co_Authorship'][0],
                            data['Co_Authors_per_Doc'][0],
                            data['Authors_Keywords_DE'][0],
                            data['References_per_Doc'][0],
                            data['Document_Average_Age'][0],
                            data['Average_Citations_per_Doc'][0]
                        ]
                    })
                    report_excel.set(add_to_report(report_choices, report_excel, [df_box], [], "maininfo"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Main Information added to report", duration=5, close_button=False)

            @reactive.calc
            def main_informations():
                # Show a modal while loading
                def loading_modal():
                    # --- Nice loading modal with rotating phrases ---
                    phrases = [
                        "⏳ Loading... Please wait.",
                        "🔍 Crunching bibliometric numbers...",
                        "📚 Counting references and citations...",
                        "🧠 Mapping science, one paper at a time...",
                        "✨ Almost there! Preparing your dashboard...",
                        # "🤖 Summoning BiblioAI for insights...",
                        "📈 Calculating main indicators...",
                        "🔗 Connecting authors and sources...",
                        "🌐 Exploring your scientific landscape...",
                        "🕵️‍♂️ Detecting trends and patterns...",
                        "🚀 Science mapping in progress...",
                    ]
                    # The modal content will have a span with id="loading-phrase"
                    modal = ui.modal(
                        ui.div(
                            ui.img(
                                src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                height="150px",
                                style="display: block; margin: 0 auto; text-align: center;",
                            ),
                            ui.h4(
                                phrases[0],
                                id="loading-phrase",
                                style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                            ),
                        ),
                        easy_close=False,
                        footer=None,
                    )
                    # Inject JS to rotate phrases every 1s
                    js = f"""
                    <script>
                    (function() {{
                        var phrases = {phrases};
                        var idx = 0;
                        var el = document.getElementById('loading-phrase');
                        if (el) {{
                            setInterval(function() {{
                                idx = (idx + 1) % phrases.length;
                                el.textContent = phrases[idx];
                            }}, 1000);
                        }}
                    }})();
                    </script>
                    """
                    return ui.HTML(str(modal) + js)
                ui.modal_show(loading_modal())
                try:
                    result = get_main_informations(df)
                    return result
                finally:
                    ui.modal_remove()
            
            with ui.card(full_screen=True, fill=True):
                @render.express()
                def show_informations():
                    data = main_informations()
                    temp = df_informations.set(data)
                    with ui.navset_underline(id="tab"):
                        with ui.nav_panel("Box"):
                            ui.p("") #spazio
                            with ui.layout_column_wrap(width=1 / 4):
                                with ui.value_box(showcase=ICONS["timespan"], theme="bg-gradient-blue-purple"):
                                    "Timespan"
                                    ui.h2(
                                        f"{data['Min_Year'][0]} - {data['Max_Year'][0]}"
                                    )
                                with ui.value_box(showcase=ICONS["sources"], theme="bg-gradient-blue-purple"):
                                    "Sources"
                                    ui.h2(
                                        f"{data['Unique_SO'][0]}"
                                    )
                                with ui.value_box(showcase=ICONS["documents"], theme="bg-gradient-blue-purple"):
                                    "Documents"
                                    ui.h2(
                                        f"{len(data)}"
                                    )
                                with ui.value_box(showcase=ICONS["annual_growth_rate"], theme="bg-gradient-blue-purple"):
                                    "Annual Growth Rate"
                                    ui.h2(
                                        f"{data['CAGR'][0]} %"
                                    )
                            with ui.layout_column_wrap(width=1 / 4):
                                with ui.value_box(showcase=ICONS["authors"], theme="bg-gradient-blue-purple"):
                                    "Authors"
                                    ui.h2(
                                        f"{data['Unique_AU'][0]}"
                                    )
                                with ui.value_box(showcase=ICONS["authors_single_authored_docs"], theme="bg-gradient-blue-purple"):
                                    "Authors of single-authored docs"
                                    ui.h2(
                                        f"{data['Authors_of_single_authored_docs'][0]}"
                                    )
                                with ui.value_box(showcase=ICONS["international_co_authorship"], theme="bg-gradient-blue-purple"):
                                    "International Co-Authorship"
                                    ui.h2(
                                        f"{data['International_Co_Authorship'][0]} %"
                                    )
                                with ui.value_box(showcase=ICONS["co_authors_per_doc"], theme="bg-gradient-blue-purple"):
                                    "Co-Authors per Doc"
                                    ui.h2(
                                        f"{data['Co_Authors_per_Doc'][0]}"
                                    )
                            with ui.layout_column_wrap(width=1 / 4):
                                with ui.value_box(showcase=ICONS["authors_keywords_de"], theme="bg-gradient-blue-purple"):
                                    "Author's Keywords (DE)"
                                    ui.h2(
                                        f"{data['Authors_Keywords_DE'][0]}"
                                    )
                                with ui.value_box(showcase=ICONS["references"], theme="bg-gradient-blue-purple"):
                                    "References"
                                    ui.h2(
                                        f"{data['References_per_Doc'][0]}"
                                    )

                                with ui.value_box(showcase=ICONS["document_average_age"], theme="bg-gradient-blue-purple"):
                                    "Document Average Age"
                                    ui.h2(
                                        f"{data['Document_Average_Age'][0]}"
                                    )
                                with ui.value_box(showcase=ICONS["average_citations_per_doc"], theme="bg-gradient-blue-purple"):
                                    "Average citations per doc"
                                    ui.h2(
                                        f"{data['Average_Citations_per_Doc'][0]}"
                                    )

                        with ui.nav_panel("Table"):
                            ui.p("")

                            @render.ui
                            def table_informations():
                                data = df_informations.get()
                                df_box = pd.DataFrame({
                                    "Metric": [
                                        "Timespan",
                                        "Sources",
                                        "Documents",
                                        "Annual Growth Rate",
                                        "Authors",
                                        "Authors of single-authored docs",
                                        "International Co-Authorship",
                                        "Co-Authors per Doc",
                                        "Author's Keywords (DE)",
                                        "References",
                                        "Document Average Age",
                                        "Average citations per doc"
                                    ],
                                    "Value": [
                                        f"{data['Min_Year'][0]} - {data['Max_Year'][0]}",
                                        data['SO'].nunique(),
                                        len(data),
                                        data['CAGR'][0],
                                        data['AU'].explode().nunique(),
                                        data['Authors_of_single_authored_docs'][0],
                                        data['International_Co_Authorship'][0],
                                        data['Co_Authors_per_Doc'][0],
                                        data['Authors_Keywords_DE'][0],
                                        data['References_per_Doc'][0],
                                        data['Document_Average_Age'][0],
                                        data['Average_Citations_per_Doc'][0]
                                    ]
                                })
                                return ui.HTML(DT(df_box, style="width=100%;"))
        
        # --- Annual Scientific Production Section ---
        with ui.nav_panel("None", value="annual_scientific_production"):
            with ui.layout_columns(
                col_widths=(9, 3),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📈 Annual Scientific Production", style="color: #5567BB;")
                    ui.p("The annual scientific production of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px;"):
                    ui.input_action_button("annual_production_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"AnnualScientificProduction-{todaydate}.png"
                    )
                    def download_annual_production():
                        plot_annual_production, _ = annual_informations()
                        yield plotly_download(
                            plot_annual_production,
                            title="Annual Scientific Production",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.annual_production_report)
                def show_annual_production_report():
                    plots, publications_per_year = annual_informations()
                    report_excel.set(add_to_report(report_choices, report_excel, [publications_per_year], [plots], "annualsciprod"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Annual Scientific Production added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                @reactive.calc
                def annual_informations():
                    return get_annual_production(df)

                with ui.navset_underline(id="annual_tab"):
                    with ui.nav_panel("Plot"):
                        @render_widget
                        def show_annual_production():
                            plot_annual_production, publications_per_year = annual_informations()
                            return plot_annual_production
                    
                    with ui.nav_panel("Table"):
                        @render.ui
                        def table_annual_production():
                            _, publications_per_year = annual_informations()
                            return ui.HTML(DT(publications_per_year, style="width=100%;"))

            # AI bot Gemini Chat Integration
            # --- Floating Chat Button ---
            @render.express()
            @reactive.event(input.go_annual_scientific_production)
            def floating_chat_button():
                # Floating chat button: the image itself is the button (no extra div, no background)
                ui.tags.img(
                    src="https://i.ibb.co/hRDpGMqS/logoAI.png",
                    style=(
                        "position: fixed; bottom: 30px; right: 30px; z-index: 9999; "
                        "height: 60px; cursor: pointer; background: none;"
                    ),
                    alt="Bibliometrix",
                    onclick="document.getElementById('chat-modal').style.display = (document.getElementById('chat-modal').style.display === 'block' ? 'none' : 'block');"
                )
                
                # --- Chat Modal (hidden by default) ---
                with ui.tags.div(
                    id="chat-modal",
                    style=(
                        "display: none; position: fixed; bottom: 100px; right: 40px; z-index: 10000;"
                        "background: white; border-radius: 16px 16px 16px 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.25);"
                        "width: 400px; max-width: 90vw; max-height: 70vh; overflow-x: hidden; overflow-y: auto;"
                    )
                ):
                    with ui.tags.div(style="position: sticky; top: 0; z-index: 10; min-height: 48px; display: flex; justify-content: flex-end; align-items: center; background: #5567BB; border-radius: 16px 16px 0 0;"):
                        ui.tags.span(
                            "BiblioAI ✨",
                            style=(
                                "flex:1; color: white; font-weight: bold; font-size: 1.1rem; padding-left: 16px;"
                            )
                        )
                        ui.tags.button(
                            "✖",
                            style=(
                                "background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; padding: 8px 16px;"
                            ),
                            onclick="document.getElementById('chat-modal').style.display = 'none';"
                        )
                    # --- Chat UI ---
                    chat = ui.Chat(id="chat")
                    chat.ui(messages=["Welcome! Ask about the current plot or table."], icon_assistant="✨", style="padding: 10px")

                    # You should set your Gemini API key as an environment variable or config
                    GEMINI_API_KEY = gemini_api_key.get()
                    if GEMINI_API_KEY:
                        client = genai.Client(api_key=GEMINI_API_KEY)
                    else:
                        client = None

                    # Helper: get current plot/table context (simplified, you may want to expand this)
                    def get_current_context():
                        # This function should extract the current plot/table context
                        plot_annual_production, tab_annual_production = annual_informations()
                        return {
                            "panel": input.hidden_tabs(),
                            "plot": plot_annual_production,
                            "table": tab_annual_production,
                        }

                    # Gemini Chat Integration - handle chat messages
                    @chat.on_user_submit
                    async def handle_user_input(user_input: str):
                        if not user_input:
                            return
                        context = get_current_context()
                        user_question = user_input

                        # Check if analysis has been run
                        # No need to check since we're using @reactive.calc now

                        # Compose prompt for Gemini
                        prompt = (
                            f"You are an expert assistant for a bibliometric analysis dashboard. "
                            f"The user is currently viewing the '{context['panel']}' section. "
                            f"Provide helpful, concise information about the plot and table shown in this section. "
                            f"If the user asks about the plot or table, answer based on the context. "
                            f"User question: {user_question}"
                            f"Table: {context['table'].to_json()} "
                        )
                        if client is not None:
                            try:
                                response = client.models.generate_content(
                                    model="gemini-2.0-flash",
                                    contents=[
                                    types.Part.from_bytes(
                                        data=context['plot'].to_image(format="png", scale=1),
                                        mime_type='image/png',
                                    ),
                                    prompt
                                    ]
                                )
                                answer = response.text
                            except Exception:
                                answer = "Sorry, the AI service is currently unavailable."
                        else:
                            answer = "Gemini API key not configured. Please set GEMINI_API_KEY in Settings section."

                        await chat.append_message(answer)
        
        # --- Average Citations per Year Section ---
        with ui.nav_panel("None", value="average_citations_per_year"):
            with ui.layout_columns(
                col_widths=(9, 3),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("❞ Average Citations per Year", style="color: #5567BB;")
                    ui.p("The average citations per year of the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px;"):
                    ui.input_action_button("average_citations_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"AverageCitations-{todaydate}.png"
                    )
                    def download_average_citations():
                        plot_average_citations, _ = average_citations()
                        yield plotly_download(
                            plot_average_citations,
                            title="Average Citations per Year",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.average_citations_report)
                def show_average_citations_report():
                    plots, publications = average_citations()
                    report_excel.set(add_to_report(report_choices, report_excel, [publications], [plots], "averagecitperyear"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Average Citations per Year added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                @reactive.calc
                def average_citations():
                    return get_average_citations(df)

                with ui.navset_underline(id="average_tab"):
                    with ui.nav_panel("Plot"):
                        @render_widget
                        def show_average_citations():
                            plot_average_citations, avg_citations = average_citations()
                            return plot_average_citations
                    
                    with ui.nav_panel("Table"):
                        @render.ui
                        def table_average_citations():
                            _, avg_citations = average_citations()
                            return ui.HTML(DT(avg_citations, style="width=100%;"))
        
        # --- Three-Field Plot Section ---
        with ui.nav_panel("None", value="three_field_plot"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🪢 Three-Field Plot", style="color: #5567BB;")
                    ui.p("The three-field plot of the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_three_field_plot", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("three_field_plot_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"ThreeFieldPlot-{todaydate}.png"
                    )
                    def download_three_field_plot():
                        result = three_field_plot_results.get()
                        if result is None:
                            yield b""
                            return
                        yield plotly_download(
                            result,
                            title="Three-Field Plot",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.three_field_plot_report)
                def show_three_field_plot_report():
                    result = three_field_plot_results.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first by clicking the Run Analysis button", duration=5, close_button=False, type="warning")
                    report_excel.set(add_to_report(report_choices, report_excel, [], [result], "threefieldsplot"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Three-Field Plot added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=True):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_three_field", position="right", ):
                        field_options = {"AU": "Authors", "CR": "References", "DE": "Keywords", "SO": "Sources", "CR_SO": "Cited Sources", "AU_UN": "Affiliations", "AU_CO": "Countries", "ID": "Keywords Plus", "TI_TM": "Titles", "AB_TM": "Abstract", "CR_SO": "Cited Sources"}
                        # if database == "Dimensions" or database == "PubMed" or database == "Cochrane" or database == "Lens":
                        #     del field_options["CR"]
                        #     del field_options["CR_SO"]
                        
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the three-field plot.")
                        with ui.accordion(id="acc_tfp", multiple=True, open=False):
                            with ui.accordion_panel("Middle Field"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("middle_field", "Field:", field_options, selected=list(field_options.keys())[0])
                                    ui.input_numeric("middle_field_items", "Items:", value=20)
                            with ui.accordion_panel("Left Field"):   
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("left_field", "Field:", field_options, selected=list(field_options.keys())[1])
                                    ui.input_numeric("left_field_items", "Items:", value=20)
                            with ui.accordion_panel("Right Field"):    
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("right_field", "Field:", field_options, selected=list(field_options.keys())[2])
                                    ui.input_numeric("right_field_items", "Items:", value=20)

                    # Store the three field plot results
                    three_field_plot_results = reactive.Value(None)
                    
                    @reactive.effect
                    @reactive.event(input.run_three_field_plot)
                    def calculate_three_field_plot():
                        # Use optimized loading modal
                        ui.modal_show(create_loading_modal("three-field plot"))
                        try:
                            left_field = input.left_field()
                            middle_field = input.middle_field()
                            right_field = input.right_field()
                            left_field_items = input.left_field_items()
                            middle_field_items = input.middle_field_items()
                            right_field_items = input.right_field_items()

                            result = get_three_field_plot(df, left_field, middle_field, right_field, left_field_items, middle_field_items, right_field_items)
                            three_field_plot_results.set(result)
                        finally:
                            ui.modal_remove()

                    @render.ui
                    def show_three_field_plot_placeholder():
                        result = three_field_plot_results.get()
                        if result is None:
                            return ui.div(
                                ui.p("Click the Run Analysis button to generate the three-field plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                style="height: 400px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                            )
                        return None
                    
                    @render_widget
                    def show_three_field_plot_widget():
                        result = three_field_plot_results.get()
                        if result is None:
                            return None
                        return result
                    
            ui.h4("Description", style="color: #5567BB;")
            ui.p("Visualize the main items of three fields (e.g. authors, keywords, journals), and how they are related through a Sankey diagram.")
            ui.p("Reference: ", style="font-weight: bold; font-size: 12px;")
            ui.p("Cobo, M. J., Lopez-Herrera, A. G., Herrera-Viedma, E., & Herrera, F. (2011). An approach for detecting, quantifying, and visualizing the evolution of a research field: A practical application to the fuzzy sets theory field. Journal of Informetrics, 5(1), 146-166.", style="font-style: italic; font-color: #cccc; font-size: 10px;")

        # --- Most Relevant Sources Section ---
        with ui.nav_panel("None", value="most_relevant_sources"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📖 Most Relevant Sources", style="color: #5567BB;")
                    ui.p("The most relevant sources of the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_relevant_sources", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_relevant_sources_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostRelevantSources-{todaydate}.png"
                    )
                    def download_most_relevant_sources():
                        result = relevant_sources_results.get()
                        if result is None:
                            yield b""
                            return
                        plot_most_relevant_sources, _ = result
                        yield plotly_download(
                            plot_most_relevant_sources,
                            title="Most Relevant Sources",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.most_relevant_sources_report)
                def show_most_relevant_sources_report():
                    result = relevant_sources_results.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first by clicking the Run Analysis button", duration=5, close_button=False, type="warning")
                    plots, relevant_sources_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [relevant_sources_tab], [plots], "mostrelsources"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Most Relevant Sources added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_relevant_sources", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most relevant sources.")
                        ui.input_numeric("num_of_sources", "Select the numbers of sources to apply to the dataset:", value=10)

                    # Store the relevant sources results
                    relevant_sources_results = reactive.Value(None)
                    
                    @reactive.effect
                    @reactive.event(input.run_relevant_sources)
                    def calculate_relevant_sources():
                        # Show loading modal while calculating
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "📖 Processing source data...",
                                "📊 Ranking sources by relevance...",
                                "🔍 Computing source metrics...",
                                "✨ Almost there! Preparing your dashboard...",
                                "📈 Calculating source indicators...",
                                "🔗 Connecting sources and data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            num_of_sources = input.num_of_sources()
                            result = get_relevant_sources(df, num_of_sources)
                            relevant_sources_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="relevant_sources_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def show_relevant_sources_placeholder():
                                result = relevant_sources_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Set the number of sources in the sidebar and click the Run Analysis button.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return None
                            
                            @render_widget
                            def show_relevant_sources_widget():
                                result = relevant_sources_results.get()
                                if result is None:
                                    return None
                                plot_relevant_sources, _ = result
                                return plot_relevant_sources
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_relevant_sources():
                                result = relevant_sources_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the relevant sources data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, relevant_sources_tab = result
                                return ui.HTML(DT(relevant_sources_tab, style="width=100%;"))
        
        # --- Most Local Cited Sources Section ---
        with ui.nav_panel("None", value="most_local_cited_sources"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📖 Most Local Cited Sources", style="color: #5567BB;")
                    ui.p("The most local cited sources of the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_local_cited_sources", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_local_cited_sources_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostLocalCitedSources-{todaydate}.png"
                    )
                    def download_most_local_cited_sources():
                        result = local_cited_sources_results.get()
                        if result is None:
                            yield b""
                            return
                        plot_most_local_cited_sources, _ = result
                        yield plotly_download(
                            plot_most_local_cited_sources,
                            title="Most Local Cited Sources",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.most_local_cited_sources_report)
                def show_most_local_cited_sources_report():
                    result = local_cited_sources_results.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first by clicking the Run Analysis button", duration=5, close_button=False, type="warning")
                    plots, local_cited_sources_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [local_cited_sources_tab], [plots], "mostloccitsources"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Most Local Cited Sources added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_local_cited_sources", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most local cited sources.")
                        ui.input_numeric("num_of_cited_sources", "Select the numbers of sources to apply to the dataset:", value=10)

                    # Store the local cited sources results
                    local_cited_sources_results = reactive.Value(None)
                    
                    @reactive.effect
                    @reactive.event(input.run_local_cited_sources)
                    def calculate_local_cited_sources():
                        # Show loading modal while calculating
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "📖 Processing local citation data...",
                                "📊 Ranking locally cited sources...",
                                "🔍 Computing citation metrics...",
                                "✨ Almost there! Preparing your dashboard...",
                                "📈 Calculating citation indicators...",
                                "🔗 Connecting citations and sources...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            num_of_cited_sources = input.num_of_cited_sources()
                            result = get_local_cited_sources(df, num_of_cited_sources)
                            local_cited_sources_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="local_cited_sources_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def show_local_cited_sources_placeholder():
                                result = local_cited_sources_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Set the number of sources in the sidebar and click the Run Analysis button.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return None
                            
                            @render_widget
                            def show_local_cited_sources_widget():
                                result = local_cited_sources_results.get()
                                if result is None:
                                    return None
                                plot_local_cited_sources, _ = result
                                return plot_local_cited_sources
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_local_cited_sources():
                                result = local_cited_sources_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the local cited sources data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, local_cited_sources_tab = result
                                return ui.HTML(DT(local_cited_sources_tab, style="width=100%;"))
        
        # --- Bradford's Law Section ---
        with ui.nav_panel("None", value="bradfords_law"):
            with ui.layout_columns(
                col_widths=(9, 3),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📖 Bradford's Law", style="color: #5567BB;")
                    ui.p("The application of Bradford's Law to the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px;"):
                    ui.input_action_button("bradfords_law_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"BradfordsLaw-{todaydate}.png"
                    )
                    def download_bradfords_law():
                        plot_bradfords_law, _ = bradford_law()
                        yield plotly_download(
                            plot_bradfords_law,
                            title="Bradford's Law",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.bradfords_law_report)
                def show_bradfords_law_report():
                    plots, bradford_law_tab = bradford_law()
                    report_excel.set(add_to_report(report_choices, report_excel, [bradford_law_tab], [plots], "bradfordlaw"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Bradford's Law added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                @reactive.calc
                def bradford_law():
                    return get_bradford_law(df)

                with ui.navset_underline(id="bradford_law_tab"):
                    with ui.nav_panel("Plot"):
                        @render_widget
                        def show_bradford_law():
                            plot_bradford_law, _ = bradford_law()
                            return plot_bradford_law
                    
                    with ui.nav_panel("Table"):
                        @render.ui
                        def table_bradford_law():
                            _, bradford_law_tab = bradford_law()
                            return ui.HTML(DT(bradford_law_tab, style="width=100%;"))
        
        # --- Sources' Local Impact Section ---
        with ui.nav_panel("None", value="sources_local_impact"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📖 Sources' Local Impact", style="color: #5567BB;")
                    ui.p("The sources' local impact of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_sources_local_impact", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("sources_local_impact_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"SourcesLocalImpact-{todaydate}.png"
                    )
                    def download_sources_local_impact():
                        result = sources_local_impact_results.get()
                        if result is None:
                            yield b""
                            return
                        plot_sources_local_impact, _ = result
                        yield plotly_download(
                            plot_sources_local_impact,
                            title="Sources' Local Impact",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.sources_local_impact_report)
                def show_sources_local_impact_report():
                    result = sources_local_impact_results.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first by clicking the Run Analysis button", duration=5, close_button=False, type="warning")
                    plots, sources_local_impact_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [sources_local_impact_tab], [plots], "sourcelocimpact"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Sources' Local Impact added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_sources_local_impact", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the sources' local impact.")
                        ui.input_numeric("num_of_sources_local_impact", "Select the numbers of sources to apply to the dataset:", value=10)
                        ui.input_select("source_local_impact", "Impact measure", {"h_index": "H-Index", "g_index": "G-Index", "m_index": "M-index", "total_cit": "Total Citation"}, selected="h_index")

                    # Store the sources local impact results
                    sources_local_impact_results = reactive.Value(None)
                    
                    @reactive.effect
                    @reactive.event(input.run_sources_local_impact)
                    def calculate_sources_local_impact():
                        # Show loading modal while calculating
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "📖 Processing impact metrics...",
                                "📊 Computing local impact scores...",
                                "🔍 Ranking sources by impact...",
                                "✨ Almost there! Preparing your dashboard...",
                                "📈 Calculating impact indicators...",
                                "🔗 Connecting sources and impact data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            num_of_sources_local_impact = input.num_of_sources_local_impact()
                            source_local_impact = input.source_local_impact()
                            result = get_sources_local_impact(df, num_of_sources_local_impact, source_local_impact)
                            sources_local_impact_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="sources_local_impact_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def show_sources_local_impact_placeholder():
                                result = sources_local_impact_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the Sources' Local Impact analysis.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return None
                            
                            @render_widget
                            def show_sources_local_impact_widget():
                                result = sources_local_impact_results.get()
                                if result is None:
                                    return None
                                plot_sources_local_impact, _ = result
                                return plot_sources_local_impact
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_sources_local_impact():
                                result = sources_local_impact_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the sources' local impact data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, sources_local_impact_tab = result
                                return ui.HTML(DT(sources_local_impact_tab, style="width=100%;"))
        
        # --- Sources' Production ---
        with ui.nav_panel("None", value="sources_production"):
            sources_production_result = reactive.value(None)
            
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📖 Sources' Production over Time", style="color: #5567BB;")
                    ui.p("The sources' production over time of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_sources_production", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("sources_production_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"SourcesProduction-{todaydate}.png"
                    )
                    def download_sources_production():
                        result = sources_production_result.get()
                        if result is None:
                            return None
                        plot_sources_production, _ = result
                        yield plotly_download(
                            plot_sources_production,
                            title="Sources' Production over Time",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.sources_production_report)
                def show_sources_production_report():
                    result = sources_production_result.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=5, type="warning")
                    plots, sources_production_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [sources_production_tab], [plots], "sourceprodovertime"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Sources' Production over Time added to report", duration=5, close_button=False)

            @reactive.effect
            @reactive.event(input.run_sources_production)
            def run_sources_production_analysis():
                # Show loading modal while calculating (same style as Main Information)
                def loading_modal():
                    phrases = [
                        "⏳ Loading... Please wait.",
                        "📊 Processing temporal data...",
                        "📈 Calculating production metrics...",
                        "🔍 Generating time series analysis...",
                        "✨ Almost there! Preparing your dashboard...",
                        "📈 Calculating production indicators...",
                        "🔗 Connecting sources and time data...",
                        "🌐 Exploring your scientific landscape...",
                        "🚀 Science mapping in progress...",
                    ]
                    modal = ui.modal(
                        ui.div(
                            ui.img(
                                src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                height="150px",
                                style="display: block; margin: 0 auto; text-align: center;",
                            ),
                            ui.h4(
                                phrases[0],
                                id="loading-phrase",
                                style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                            ),
                        ),
                        easy_close=False,
                        footer=None,
                    )
                    js = f"""
                    <script>
                    (function() {{
                        var phrases = {phrases};
                        var idx = 0;
                        var el = document.getElementById('loading-phrase');
                        if (el) {{
                            setInterval(function() {{
                                idx = (idx + 1) % phrases.length;
                                el.textContent = phrases[idx];
                            }}, 1000);
                        }}
                    }})();
                    </script>
                    """
                    return ui.HTML(str(modal) + js)
                
                ui.modal_show(loading_modal())
                try:
                    num_of_sources_production = input.num_of_sources_production()
                    occurences = input.occurences()
                    result = get_sources_production(df, num_of_sources_production, occurences)
                    sources_production_result.set(result)
                finally:
                    ui.modal_remove()

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_sources_production", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the sources' production over time.")
                        ui.input_select("occurences", "Select the number of occurrences to apply to the dataset:", {"cumulative": "Cumulate", "year": "Per Year"}, selected="cum")
                        ui.input_slider("num_of_sources_production", "Select the numbers of sources to apply to the dataset:", sep="", ticks=True, min=1, max=50, value=5, step=1)

                    with ui.navset_underline(id="sources_production_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def sources_production_placeholder():
                                result = sources_production_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the sources' production over time visualization.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # Render the widget directly when result is available
                                plot_sources_production, _ = result
                                return plot_sources_production
                            
                            @render_widget  
                            def show_sources_production():
                                result = sources_production_result.get()
                                if result is None:
                                    return None
                                plot_sources_production, _ = result
                                return plot_sources_production
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_sources_production():
                                result = sources_production_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the sources' production data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, sources_production_tab = result
                                return ui.HTML(DT(sources_production_tab, style="width=100%;"))
        
        # --- Most Relevant Authors Section ---
        with ui.nav_panel("None", value="most_relevant_authors"):
            relevant_authors_result = reactive.value(None)
            
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("👤 Most Relevant Authors", style="color: #5567BB;")
                    ui.p("The most relevant authors of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_most_relevant_authors", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_relevant_authors_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostRelevantAuthors-{todaydate}.png"
                    )
                    def download_most_relevant_authors():
                        result = relevant_authors_result.get()
                        if result is None:
                            return None
                        plot_most_relevant_authors, _ = result
                        yield plotly_download(
                            plot_most_relevant_authors,
                            title="Most Relevant Authors",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.most_relevant_authors_report)
                def show_most_relevant_authors_report():
                    result = relevant_authors_result.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=5, type="warning")
                    plots, relevant_authors_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [relevant_authors_tab], [plots], "mostrelauthors"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Most Relevant Authors added to report", duration=5, close_button=False)

            @reactive.effect
            @reactive.event(input.run_most_relevant_authors)
            def run_relevant_authors_analysis():
                # Show loading modal while calculating (same style as Sources Production over Time)
                def loading_modal():
                    phrases = [
                        "⏳ Loading... Please wait.",
                        "🔍 Analyzing author relevance...",
                        "📊 Processing author data...",
                        "📈 Calculating relevance metrics...",
                        "⏳ Ranking most relevant authors...",
                        "✨ Almost there! Preparing your dashboard...",
                        "🎯 Finalizing author visualization...",
                        "🔗 Connecting authors and impact data...",
                        "🌐 Exploring your scientific landscape...",
                        "🚀 Science mapping in progress...",
                    ]
                    modal = ui.modal(
                        ui.div(
                            ui.img(
                                src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                height="150px",
                                style="display: block; margin: 0 auto; text-align: center;",
                            ),
                            ui.h4(
                                phrases[0],
                                id="loading-phrase",
                                style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                            ),
                        ),
                        easy_close=False,
                        footer=None,
                    )
                    js = f"""
                    <script>
                    (function() {{
                        var phrases = {phrases};
                        var idx = 0;
                        var el = document.getElementById('loading-phrase');
                        if (el) {{
                            setInterval(function() {{
                                idx = (idx + 1) % phrases.length;
                                el.textContent = phrases[idx];
                            }}, 1000);
                        }}
                    }})();
                    </script>
                    """
                    return ui.HTML(str(modal) + js)
                
                ui.modal_show(loading_modal())
                try:
                    num_of_authors = input.num_of_authors()
                    frequency = input.frequency()
                    result = get_relevant_authors(df, num_of_authors, frequency)
                    relevant_authors_result.set(result)
                finally:
                    ui.modal_remove()

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_relevant_authors", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most relevant authors.")
                        ui.input_numeric("num_of_authors", "Select the number of authors to apply to the dataset:", value=10)
                        ui.input_select("frequency", "Frequency measure", {"n_docs": "N. of Documents", "percentage": "Percentage", "freq_measure": "Fractionalized Frequency"}, selected="n_docs")

                    with ui.navset_underline(id="most_relevant_authors_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def relevant_authors_placeholder():
                                result = relevant_authors_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the most relevant authors visualization.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # Render the widget directly when result is available
                                plot_relevant_authors, _ = result
                                return plot_relevant_authors
                            
                            @render_widget
                            def show_relevant_authors():
                                result = relevant_authors_result.get()
                                if result is None:
                                    return None
                                plot_relevant_authors, _ = result
                                return plot_relevant_authors
                    
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_relevant_authors():
                                result = relevant_authors_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the most relevant authors data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, relevant_authors_tab = result
                                return ui.HTML(DT(relevant_authors_tab, style="width=100%;"))
        
        # --- Most Local Cited Authors Section ---
        with ui.nav_panel("None", value="most_local_cited_authors"):
            local_cited_authors_result = reactive.value(None)
            
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("👤 Most Local Cited Authors", style="color: #5567BB;")
                    ui.p("The most local cited authors of the dataset")

                # --- FIX: move the buttons to the correct column for alignment ---
                with ui.tags.div(
                    style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"
                ):
                    ui.input_action_button("run_most_local_cited_authors", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_local_cited_authors_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostLocalCitedAuthors-{todaydate}.png"
                    )
                    def download_most_local_cited_authors():
                        result = local_cited_authors_result.get()
                        if result is None:
                            return None
                        plot_most_local_cited_authors, _ = result
                        yield plotly_download(
                            plot_most_local_cited_authors,
                            title="Most Local Cited Authors",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.most_local_cited_authors_report)
                def show_most_local_cited_authors_report():
                    result = local_cited_authors_result.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=5, type="warning")
                    plots, local_cited_authors_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [local_cited_authors_tab], [plots], "mostloccitauthors"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Most Local Cited Authors added to report", duration=5, close_button=False)

            @reactive.effect
            @reactive.event(input.run_most_local_cited_authors)
            def run_local_cited_authors_analysis():
                # Show loading modal while calculating (same style as Sources Production over Time)
                def loading_modal():
                    phrases = [
                        "⏳ Loading... Please wait.",
                        "🔍 Analyzing local cited authors...",
                        "📊 Processing citation data...",
                        "📈 Calculating local citation metrics...",
                        "⏳ Ranking most cited authors...",
                        "✨ Almost there! Preparing your dashboard...",
                        "🎯 Finalizing local citations visualization...",
                        "🔗 Connecting citation and author data...",
                        "🌐 Exploring your scientific landscape...",
                        "🚀 Science mapping in progress...",
                    ]
                    modal = ui.modal(
                        ui.div(
                            ui.img(
                                src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                height="150px",
                                style="display: block; margin: 0 auto; text-align: center;",
                            ),
                            ui.h4(
                                phrases[0],
                                id="loading-phrase",
                                style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                            ),
                        ),
                        easy_close=False,
                        footer=None,
                    )
                    js = f"""
                    <script>
                    (function() {{
                        var phrases = {phrases};
                        var idx = 0;
                        var el = document.getElementById('loading-phrase');
                        if (el) {{
                            setInterval(function() {{
                                idx = (idx + 1) % phrases.length;
                                el.textContent = phrases[idx];
                            }}, 1000);
                        }}
                    }})();
                    </script>
                    """
                    return ui.HTML(str(modal) + js)
                
                ui.modal_show(loading_modal())
                try:
                    num_of_cited_authors = input.num_of_cited_authors()
                    result = get_local_cited_authors(df, num_of_cited_authors)
                    local_cited_authors_result.set(result)
                finally:
                    ui.modal_remove()

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_local_cited_authors", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most local cited authors.")
                        ui.input_numeric("num_of_cited_authors", "Select the number of authors to apply to the dataset:", value=10)

                    with ui.navset_underline(id="most_local_cited_authors_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def local_cited_authors_placeholder():
                                result = local_cited_authors_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the most local cited authors visualization.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # Render the widget directly when result is available
                                plot_local_cited_authors, _ = result
                                return plot_local_cited_authors
                            
                            @render_widget
                            def show_local_cited_authors():
                                result = local_cited_authors_result.get()
                                if result is None:
                                    return None
                                plot_local_cited_authors, _ = result
                                return plot_local_cited_authors
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_local_cited_authors():
                                result = local_cited_authors_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the most local cited authors data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, local_cited_authors_tab = result
                                return ui.HTML(DT(local_cited_authors_tab, style="width=100%;"))
        
        # --- Authors' Production over Time Section ---
        with ui.nav_panel("None", value="authors_production"):
            au_over_time_result = reactive.value(None)
            
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("👤 Authors' Production over Time", style="color: #5567BB;")
                    ui.p("The authors' production over time of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_authors_production", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("authors_production_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"AuthorsProduction-{todaydate}.png"
                    )
                    def download_authors_production():
                        result = au_over_time_result.get()
                        if result is None:
                            return None
                        plot_authors_production, _, _ = result
                        yield plotly_download(
                            plot_authors_production,
                            title="Authors' Production over Time",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.authors_production_report)
                def show_authors_production_report():
                    result = au_over_time_result.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=5, type="warning")
                    plots, authors_production_tab, documents_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [authors_production_tab, documents_tab], [plots], "authorprodovertime"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Authors' Production over Time added to report", duration=5, close_button=False)

            @reactive.effect
            @reactive.event(input.run_authors_production)
            def run_authors_production_analysis():
                # Show loading modal while calculating (same style as Sources Production over Time)
                def loading_modal():
                    phrases = [
                        "⏳ Loading... Please wait.",
                        "🔍 Analyzing authors' production patterns...",
                        "📊 Processing temporal author data...",
                        "📈 Calculating production metrics over time...",
                        "⏳ Generating author timeline analysis...",
                        "✨ Almost there! Preparing your dashboard...",
                        "🎯 Finalizing authors' production visualization...",
                        "🔗 Connecting authors and time data...",
                        "🌐 Exploring your scientific landscape...",
                        "🚀 Science mapping in progress...",
                    ]
                    modal = ui.modal(
                        ui.div(
                            ui.img(
                                src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                height="150px",
                                style="display: block; margin: 0 auto; text-align: center;",
                            ),
                            ui.h4(
                                phrases[0],
                                id="loading-phrase",
                                style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                            ),
                        ),
                        easy_close=False,
                        footer=None,
                    )
                    js = f"""
                    <script>
                    (function() {{
                        var phrases = {phrases};
                        var idx = 0;
                        var el = document.getElementById('loading-phrase');
                        if (el) {{
                            setInterval(function() {{
                                idx = (idx + 1) % phrases.length;
                                el.textContent = phrases[idx];
                            }}, 1000);
                        }}
                    }})();
                    </script>
                    """
                    return ui.HTML(str(modal) + js)
                
                ui.modal_show(loading_modal())
                try:
                    top_k_authors = input.TopAuthorsProdK()
                    result = get_author_production_over_time(df, top_k_authors)
                    au_over_time_result.set(result)
                finally:
                    ui.modal_remove()

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_authors_production", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the authors' production over time.")
                        ui.input_numeric("TopAuthorsProdK", "Select the number of top authors to display:", value=10)

                    with ui.navset_underline(id="authors_production_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def authors_production_placeholder():
                                result = au_over_time_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the authors' production over time visualization.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # Render the widget directly when result is available
                                plot_authors_production, _, _ = result
                                return plot_authors_production
                            
                            @render_widget
                            def show_authors_production():
                                result = au_over_time_result.get()
                                if result is None:
                                    return None
                                plot_authors_production, _, _ = result
                                return plot_authors_production
                        
                        with ui.nav_panel("Table - Production per year"):
                            @render.ui
                            def table_authors_production():
                                result = au_over_time_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the authors' production per year data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, table_authors_production, _ = result
                                return ui.HTML(DT(table_authors_production, style="width=100%;"))

                        with ui.nav_panel("Table - Documents"):
                            @render.ui
                            def table_documents():
                                result = au_over_time_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the authors' documents data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, _, table_documents = result
                                if "DOI" in table_documents.columns:
                                    # Gestione dei link DOI
                                    table_documents['DOI'] = table_documents['DOI'].fillna("N/A")
                                    table_documents['DOI'] = table_documents['DOI'].apply(
                                        lambda x: f'<a href="https://doi.org/{x}" target="_blank">{x}</a>' if x != "N/A" else x
                                    )
                                return ui.HTML(DT(table_documents, style="width=100%;"))
                    # AI bot Gemini Chat Integration
            # --- Floating Chat Button ---
            @render.express()
            @reactive.event(input.go_authors_production_over_time)
            def floating_chat_button_authors_production():
                # Floating chat button: the image itself is the button (no extra div, no background)
                ui.tags.img(
                    src="https://i.ibb.co/hRDpGMqS/logoAI.png",
                    style=(
                        "position: fixed; bottom: 30px; right: 30px; z-index: 9999; "
                        "height: 60px; cursor: pointer; background: none;"
                    ),
                    alt="Bibliometrix",
                    onclick="document.getElementById('chat-modal').style.display = (document.getElementById('chat-modal').style.display === 'block' ? 'none' : 'block');"
                )
                
                # --- Chat Modal (hidden by default) ---
                with ui.tags.div(
                    id="chat-modal",
                    style=(
                        "display: none; position: fixed; bottom: 100px; right: 40px; z-index: 10000;"
                        "background: white; border-radius: 16px 16px 16px 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.25);"
                        "width: 400px; max-width: 90vw; max-height: 70vh; overflow-x: hidden; overflow-y: auto;"
                    )
                ):
                    with ui.tags.div(style="position: sticky; top: 0; z-index: 10; min-height: 48px; display: flex; justify-content: flex-end; align-items: center; background: #5567BB; border-radius: 16px 16px 0 0;"):
                        ui.tags.span(
                            "BiblioAI ✨",
                            style=(
                                "flex:1; color: white; font-weight: bold; font-size: 1.1rem; padding-left: 16px;"
                            )
                        )
                        ui.tags.button(
                            "✖",
                            style=(
                                "background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; padding: 8px 16px;"
                            ),
                            onclick="document.getElementById('chat-modal').style.display = 'none';"
                        )
                    # --- Chat UI ---
                    chat = ui.Chat(id="chat_authors_production")
                    chat.ui(messages=["Welcome! Ask about the current plot or table."], icon_assistant="✨", style="padding: 10px")

                    # You should set your Gemini API key as an environment variable or config
                    GEMINI_API_KEY = gemini_api_key.get()
                    if GEMINI_API_KEY:
                        client = genai.Client(api_key=GEMINI_API_KEY)
                    else:
                        client = None

                    # Helper: get current plot/table context (simplified, you may want to expand this)
                    def get_current_context():
                        # This function should extract the current plot/table context
                        plot_authors_production, table_authors_production, table_documents = au_over_time()
                        return {
                            "panel": input.hidden_tabs(),
                            "plot": plot_authors_production,
                            "table": [table_authors_production, table_documents],
                        }

                    # Gemini Chat Integration - handle chat messages
                    @chat.on_user_submit
                    async def handle_user_input(user_input: str):
                        if not user_input:
                            return
                        context = get_current_context()
                        user_question = user_input

                        # Compose prompt for Gemini
                        prompt = (
                            f"You are an expert assistant for a bibliometric analysis dashboard. "
                            f"The user is currently viewing the '{context['panel']}' section. "
                            f"Provide helpful, concise information about the plot and table shown in this section. "
                            f"If the user asks about the plots or tables, answer based on the context. "
                            f"User question: {user_question}"
                        )
                        for i, table in enumerate(context['table']):
                            prompt += f"\nTable {i}: {table.to_json(orient='records')}"
                        print(f"Prompt for Gemini: {prompt}")
                        if client is not None:
                            try:
                                response = client.models.generate_content(
                                    model="gemini-2.0-flash",
                                    contents=[
                                    types.Part.from_bytes(
                                        data=context['plot'].to_image(format="png", scale=1),
                                        mime_type='image/png',
                                    ),
                                    prompt
                                    ]
                                )
                                answer = response.text
                            except Exception:
                                answer = "Sorry, the AI service is currently unavailable."
                        else:
                            answer = "Gemini API key not configured. Please set GEMINI_API_KEY in Settings section."

                        await chat.append_message(answer)
        
        # --- Authors' Productivity through Lotka's Law Section ---
        with ui.nav_panel("None", value="lotka_law"):
            with ui.layout_columns(
                col_widths=(9, 3),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("👤 Author Productivity through Lotka's Law", style="color: #5567BB;")
                    ui.p("The authors' productivity through Lotka's Law of the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px;"):
                    ui.input_action_button("lotkas_law_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"LotkasLaw-{todaydate}.png"
                    )
                    def download_lotkas_law():
                        plot_lotkas_law, _ = lotka_law()
                        yield plotly_download(
                            plot_lotkas_law,
                            title="Authors' Productivity through Lotka's Law",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.lotkas_law_report)
                def show_lotkas_law_report():
                    plots, lotkas_law_tab = lotka_law()
                    report_excel.set(add_to_report(report_choices, report_excel, [lotkas_law_tab], [plots], "lotkalaw"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Authors' Productivity through Lotka's Law added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                @reactive.calc
                def lotka_law():
                    return get_lotka_law(df)

                with ui.navset_underline(id="lotka_law_tab"):
                    with ui.nav_panel("Plot"):
                        @render_widget
                        def show_lotka_law():
                            plot_lotka_law, _ = lotka_law()
                            return plot_lotka_law
                    
                    with ui.nav_panel("Table"):
                        @render.ui
                        def table_lotka_law():
                            _, lotka_law_tab = lotka_law()
                            return ui.HTML(DT(lotka_law_tab, style="width=100%;"))
        
        # --- Authors' Local Impact Section ---
        with ui.nav_panel("None", value="authors_local_impact"):
            authors_local_impact_result = reactive.value(None)
            
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("👤 Authors' Local Impact", style="color: #5567BB;")
                    ui.p("The authors' local impact of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_authors_local_impact", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("authors_local_impact_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"AuthorsLocalImpact-{todaydate}.png"
                    )
                    def download_authors_local_impact():
                        result = authors_local_impact_result.get()
                        if result is None:
                            return None
                        plot_authors_local_impact, _ = result
                        yield plotly_download(
                            plot_authors_local_impact,
                            title="Authors' Local Impact",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.authors_local_impact_report)
                def show_authors_local_impact_report():
                    result = authors_local_impact_result.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=5, type="warning")
                    plots, authors_local_impact_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [authors_local_impact_tab], [plots], "authorlocimpact"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Authors' Local Impact added to report", duration=5, close_button=False)

            @reactive.effect
            @reactive.event(input.run_authors_local_impact)
            def run_authors_local_impact_analysis():
                # Show loading modal while calculating (same style as Sources Production over Time)
                def loading_modal():
                    phrases = [
                        "⏳ Loading... Please wait.",
                        "🔍 Analyzing authors' local impact...",
                        "📊 Processing impact metrics...",
                        "📈 Calculating H-index, G-index values...",
                        "⏳ Computing citation impact scores...",
                        "✨ Almost there! Preparing your dashboard...",
                        "🎯 Finalizing authors' impact visualization...",
                        "🔗 Connecting impact and author data...",
                        "🌐 Exploring your scientific landscape...",
                        "🚀 Science mapping in progress...",
                    ]
                    modal = ui.modal(
                        ui.div(
                            ui.img(
                                src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                height="150px",
                                style="display: block; margin: 0 auto; text-align: center;",
                            ),
                            ui.h4(
                                phrases[0],
                                id="loading-phrase",
                                style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                            ),
                        ),
                        easy_close=False,
                        footer=None,
                    )
                    js = f"""
                    <script>
                    (function() {{
                        var phrases = {phrases};
                        var idx = 0;
                        var el = document.getElementById('loading-phrase');
                        if (el) {{
                            setInterval(function() {{
                                idx = (idx + 1) % phrases.length;
                                el.textContent = phrases[idx];
                            }}, 1000);
                        }}
                    }})();
                    </script>
                    """
                    return ui.HTML(str(modal) + js)
                
                ui.modal_show(loading_modal())
                try:
                    num_of_authors_local_impact = input.num_of_authors_local_impact()
                    author_local_impact = input.author_local_impact()
                    result = get_authors_local_impact(df, num_of_authors_local_impact, author_local_impact)
                    authors_local_impact_result.set(result)
                finally:
                    ui.modal_remove()

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_authors_local_impact", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the authors' local impact.")
                        ui.input_numeric("num_of_authors_local_impact", "Select the number of authors to apply to the dataset:", value=10)
                        ui.input_select("author_local_impact", "Impact measure", {"h_index": "H-Index", "g_index": "G-Index", "m_index": "M-index", "total_cit": "Total Citation"}, selected="h_index")

                    with ui.navset_underline(id="authors_local_impact_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def authors_local_impact_placeholder():
                                result = authors_local_impact_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the authors' local impact visualization.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # Render the widget directly when result is available
                                plot_authors_local_impact, _ = result
                                return plot_authors_local_impact
                            
                            @render_widget
                            def show_authors_local_impact():
                                result = authors_local_impact_result.get()
                                if result is None:
                                    return None
                                plot_authors_local_impact, _ = result
                                return plot_authors_local_impact
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_authors_local_impact():
                                result = authors_local_impact_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the authors' local impact data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, authors_local_impact_tab = result
                                return ui.HTML(DT(authors_local_impact_tab, style="width=100%;"))
        
        # --- Most Relevant Affiliations Section ---
        with ui.nav_panel("None", value="most_relevant_affiliations"):
            relevant_affiliations_result = reactive.value(None)
            
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🏫 Most Relevant Affiliations", style="color: #5567BB;")
                    ui.p("The most relevant affiliations of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_most_relevant_affiliations", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_relevant_affiliations_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostRelevantAffiliations-{todaydate}.png"
                    )
                    def download_most_relevant_affiliations():
                        result = relevant_affiliations_result.get()
                        if result is None:
                            return None
                        plot_most_relevant_affiliations, _ = result
                        yield plotly_download(
                            plot_most_relevant_affiliations,
                            title="Most Relevant Affiliations",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.most_relevant_affiliations_report)
                def show_most_relevant_affiliations_report():
                    result = relevant_affiliations_result.get()
                    if result is None:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=5, type="warning")
                    plots, relevant_affiliations_tab = result
                    report_excel.set(add_to_report(report_choices, report_excel, [relevant_affiliations_tab], [plots], "mostrelaffiliations"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Most Relevant Affiliations added to report", duration=5, close_button=False)

            @reactive.effect
            @reactive.event(input.run_most_relevant_affiliations)
            def run_relevant_affiliations_analysis():
                # Show loading modal while calculating (same style as Sources Production over Time)
                def loading_modal():
                    phrases = [
                        "⏳ Loading... Please wait.",
                        "🔍 Analyzing affiliation relevance...",
                        "🏫 Processing institutional data...",
                        "📈 Calculating affiliation metrics...",
                        "⏳ Ranking most relevant institutions...",
                        "✨ Almost there! Preparing your dashboard...",
                        "🎯 Finalizing affiliations visualization...",
                        "🔗 Connecting institutions and data...",
                        "🌐 Exploring your scientific landscape...",
                        "🚀 Science mapping in progress...",
                    ]
                    modal = ui.modal(
                        ui.div(
                            ui.img(
                                src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                height="150px",
                                style="display: block; margin: 0 auto; text-align: center;",
                            ),
                            ui.h4(
                                phrases[0],
                                id="loading-phrase",
                                style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                            ),
                        ),
                        easy_close=False,
                        footer=None,
                    )
                    js = f"""
                    <script>
                    (function() {{
                        var phrases = {phrases};
                        var idx = 0;
                        var el = document.getElementById('loading-phrase');
                        if (el) {{
                            setInterval(function() {{
                                idx = (idx + 1) % phrases.length;
                                el.textContent = phrases[idx];
                            }}, 1000);
                        }}
                    }})();
                    </script>
                    """
                    return ui.HTML(str(modal) + js)
                
                ui.modal_show(loading_modal())
                try:
                    num_of_affiliations = input.num_of_affiliations()
                    disambiguation = input.disambiguation()
                    result = get_relevant_affiliations(df, num_of_affiliations, disambiguation)
                    relevant_affiliations_result.set(result)
                finally:
                    ui.modal_remove()

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_relevant_affiliations", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most relevant affiliations.")
                        ui.input_numeric("num_of_affiliations", "Select the number of affiliations to apply to the dataset:", value=10)
                        ui.input_select("disambiguation", "Affiliation Name Disambiguation", {"yes": "Yes", "no": "No"}, selected="yes")

                    with ui.navset_underline(id="most_relevant_affiliations_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def relevant_affiliations_placeholder():
                                result = relevant_affiliations_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the most relevant affiliations visualization.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # Render the widget directly when result is available
                                plot_relevant_affiliations, _ = result
                                return plot_relevant_affiliations
                            
                            @render_widget
                            def show_relevant_affiliations():
                                result = relevant_affiliations_result.get()
                                if result is None:
                                    return None
                                plot_relevant_affiliations, _ = result
                                return plot_relevant_affiliations
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_relevant_affiliations():
                                result = relevant_affiliations_result.get()
                                if result is None:
                                    return ui.tags.div(
                                        ui.p("Click the Run Analysis button to generate the most relevant affiliations data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, relevant_affiliations_tab = result
                                return ui.HTML(DT(relevant_affiliations_tab, style="width=100%;"))
        
        # --- Affiliations' Production over Time Section ---
        with ui.nav_panel("None", value="affiliations_production"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🏫 Affiliations' Production over Time", style="color: #5567BB;")
                    ui.p("The affiliations' production over time of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_affiliations_production", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("affiliations_production_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"AffiliationsProduction-{todaydate}.png"
                    )
                    def download_affiliations_production():
                        plot_affiliations_production, _ = aff_over_time()
                        yield plotly_download(
                            plot_affiliations_production,
                            title="Affiliations' Production over Time",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.affiliations_production_report)
                def show_affiliations_production_report():
                    result = affiliations_production_results.get()
                    if result is not None:
                        plots, affiliations_production_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [affiliations_production_tab], [plots], "affovertime"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Affiliations' Production over Time added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=3, type="warning")

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_affiliations_production", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the affiliations' production over time.")
                        ui.input_numeric("TopAffProdK", "Select the number of top affiliations to display:", value=10)

                    # Reactive value to store affiliations production results
                    affiliations_production_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_affiliations_production)
                    def aff_over_time():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "📈 Analyzing affiliations production over time...",
                                "🔍 Processing affiliate data across time periods...",
                                "📊 Generating production timeline visualization...",
                                "⏳ Computing temporal patterns in affiliations...",
                                "✨ Almost there! Preparing your dashboard...",
                                "🎯 Finalizing affiliations production analysis...",
                                "🔗 Connecting affiliations and time data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            top_k_affiliations = input.TopAffProdK()
                            result = get_affiliation_production_over_time(df, top_k_affiliations)
                            affiliations_production_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="affiliations_production_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def show_affiliations_production_placeholder():
                                result = affiliations_production_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the Affiliations' Production over Time analysis.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # When result is available, show the widget
                                return None
                            
                            @render_widget
                            def show_affiliations_production():
                                result = affiliations_production_results.get()
                                if result is not None:
                                    plot_affiliations_production, _ = result
                                    return plot_affiliations_production
                        
                        with ui.nav_panel("Table - Production per year"):
                            @render.ui
                            def table_affiliations_production():
                                result = affiliations_production_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the affiliations production data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, table_affiliations_production = result
                                return ui.HTML(DT(table_affiliations_production, style="width=100%;"))
        
        # --- Affiliations' Local Impact Section ---
        with ui.nav_panel("None", value="corresponding_authors"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🌍 Corresponding Author's Countries", style="color: #5567BB;")
                    ui.p("The corresponding author's countries of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_corresponding_authors", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("corresponding_authors_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"CorrespondingAuthors-{todaydate}.png"
                    )
                    def download_corresponding_authors():
                        result = corresponding_authors_results.get()
                        if result is not None:
                            plot_corresponding_authors, _ = result
                            yield plotly_download(
                                plot_corresponding_authors,
                                title="Corresponding Authors' Countries",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.corresponding_authors_report)
                def show_corresponding_authors_report():
                    result = corresponding_authors_results.get()
                    if result is not None:
                        plots, corresponding_authors_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [corresponding_authors_tab], [plots], "corrauthcountries"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Corresponding Authors' Countries added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=3, type="warning")
                    return ui.notification_show("✅ Corresponding Authors' Countries added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_corresponding_authors", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the corresponding author's countries.")
                        ui.input_numeric("TopCountries", "Select the number of top countries to display:", value=10, min=1)
                    # Reactive value to store corresponding authors results
                    corresponding_authors_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_corresponding_authors)
                    def countries_data():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🌍 Loading country data...",
                                "🔎 Analyzing corresponding author countries...",
                                "📊 Compiling country-level statistics...",
                                "🗺️ Mapping global collaborations...",
                                "✨ Almost there! Preparing your country dashboard...",
                                "📈 Calculating country indicators...",
                                "🔗 Connecting countries and authors...",
                                "🌐 Exploring your international landscape...",
                                "🚀 Science mapping by country in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            top_k_countries = input.TopCountries()
                            result = get_corresponding_author_countries(df, top_k_countries)
                            corresponding_authors_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="corresponding_authors_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def show_countries_collaboration_placeholder():
                                result = corresponding_authors_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the Corresponding Author's Countries analysis.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # When result is available, show the widget
                                return None
                            
                            @render_widget
                            def show_countries_collaboration():
                                result = corresponding_authors_results.get()
                                if result is not None:
                                    countries_plot, _ = result
                                    return countries_plot

                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_countries_collaboration():
                                result = corresponding_authors_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the corresponding authors' countries data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, countries_table = result
                                return ui.HTML(DT(countries_table, style="width=100%;"))
        
        # --- Countries' Scientific Production Section ---
        with ui.nav_panel("None", value="countries_scientific_production"):
            with ui.layout_columns(
                col_widths=(9, 3),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🌍 Countries' Scientific Production", style="color: #5567BB;")
                    ui.p("The countries' scientific production of the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px;"):
                    ui.input_action_button("countries_scientific_production_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"CountriesScientificProduction-{todaydate}.png"
                    )
                    def download_countries_scientific_production():
                        plot_countries_scientific_production, _ = countries_production()
                        yield plotly_download(
                            plot_countries_scientific_production,
                            title="Countries' Scientific Production",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.countries_scientific_production_report)
                def show_countries_scientific_production_report():
                    plots, countries_scientific_production_tab = countries_production()
                    report_excel.set(add_to_report(report_choices, report_excel, [countries_scientific_production_tab], [plots], "countrysciprod"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Countries' Scientific Production added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                @reactive.calc
                def countries_production():
                    # Show loading modal while calculating (same style as Main Information)
                    def loading_modal():
                        phrases = [
                            "⏳ Loading... Please wait.",
                            "🌍 Analyzing countries' scientific production...",
                            "📊 Processing geographical data...",
                            "🏆 Ranking countries by production...",
                            "📈 Calculating production metrics...",
                            "✨ Almost there! Preparing your dashboard...",
                            "🎯 Finalizing countries' production analysis...",
                            "🔗 Connecting geographical and publication data...",
                            "🌐 Exploring your scientific landscape...",
                            "🚀 Science mapping in progress...",
                        ]
                        modal = ui.modal(
                            ui.div(
                                ui.img(
                                    src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                    height="150px",
                                    style="display: block; margin: 0 auto; text-align: center;",
                                ),
                                ui.h4(
                                    phrases[0],
                                    id="loading-phrase",
                                    style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                ),
                            ),
                            easy_close=False,
                            footer=None,
                        )
                        js = f"""
                        <script>
                        (function() {{
                            var phrases = {phrases};
                            var idx = 0;
                            var el = document.getElementById('loading-phrase');
                            if (el) {{
                                setInterval(function() {{
                                    idx = (idx + 1) % phrases.length;
                                    el.textContent = phrases[idx];
                                }}, 1000);
                            }}
                        }})();
                        </script>
                        """
                        return ui.HTML(str(modal) + js)
                    
                    ui.modal_show(loading_modal())
                    try:
                        result = get_countries_production(df)
                        return result
                    finally:
                        ui.modal_remove()

                with ui.navset_underline(id="countries_scientific_production_tab"):
                    with ui.nav_panel("Plot"):
                        @render_widget
                        def show_countries_production():
                            countries_plot, _ = countries_production()
                            return countries_plot

                    with ui.nav_panel("Table"):
                        @render.ui
                        def table_countries_production():
                            _, countries_table = countries_production()
                            return ui.HTML(DT(countries_table, style="width=100%;"))

        # --- Countries' Production over Time Section ---
        with ui.nav_panel("None", value="countries_production_over_time"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🌍 Countries' Production over Time", style="color: #5567BB;")
                    ui.p("The countries' production over time of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_countries_over_time", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("countries_production_over_time_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"CountriesProductionOverTime-{todaydate}.png"
                    )
                    def download_countries_production_over_time():
                        result = countries_over_time_results.get()
                        if result is not None:
                            plot_countries_production_over_time, _ = result
                            yield plotly_download(
                                plot_countries_production_over_time,
                                title="Countries' Production over Time",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.countries_production_over_time_report)
                def show_countries_production_over_time_report():
                    result = countries_over_time_results.get()
                    if result is not None:
                        plots, countries_production_over_time_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [countries_production_over_time_tab], [plots], "countryprodovertime"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Countries' Production over Time added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=3, type="warning")

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_countries_production_over_time", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the countries' production over time.")
                        ui.input_numeric("TopCountriesProdK", "Select the number of countries to display:", value=5)

                    # Reactive value to store countries over time results
                    countries_over_time_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_countries_over_time)
                    def countries_over_time():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🌍 Loading country production over time...",
                                "🔎 Analyzing scientific output by country and year...",
                                "📊 Compiling country-level publication trends...",
                                "🗺️ Mapping global research productivity over time...",
                                "✨ Almost there! Preparing your country dashboard...",
                                "📈 Calculating country indicators over time...",
                                "🔗 Connecting countries and publications...",
                                "🌐 Exploring your international scientific landscape...",
                                "🚀 Science mapping by country in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            top_k_countries = input.TopCountriesProdK()
                            result = get_countries_production_over_time(df, top_k_countries)
                            countries_over_time_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="countries_production_over_time_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def show_countries_over_time_placeholder():
                                result = countries_over_time_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the Countries' Production over Time analysis.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # When result is available, show the widget
                                return None
                            
                            @render_widget
                            def show_countries_over_time():
                                result = countries_over_time_results.get()
                                if result is not None:
                                    countries_plot, _ = result
                                    return countries_plot
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_countries_over_time():
                                result = countries_over_time_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the countries' production over time data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, countries_table = result
                                return ui.HTML(DT(countries_table, style="width=100%;"))
        
        # --- Most Cited Countries Section ---
        with ui.nav_panel("None", value="most_cited_countries"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🌍 Most Cited Countries", style="color: #5567BB;")
                    ui.p("The most cited countries of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_cited_countries", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_cited_countries_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostCitedCountries-{todaydate}.png"
                    )
                    def download_most_cited_countries():
                        result = cited_countries_results.get()
                        if result is not None:
                            plot_most_cited_countries, _ = result
                            yield plotly_download(
                                plot_most_cited_countries,
                                title="Most Cited Countries",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.most_cited_countries_report)
                def show_most_cited_countries_report():
                    result = cited_countries_results.get()
                    if result is not None:
                        plots, most_cited_countries_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [most_cited_countries_tab], [plots], "mostcitcountries"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Most Cited Countries added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", duration=3, type="warning")

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_cited_countries", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most cited countries.")
                        ui.input_numeric("num_of_cited_countries", "Select the number of countries to apply to the dataset:", value=10)
                        ui.input_select("cited_countries", "Citation measure", {"total_cit": "Total Citation", "average_cit": "Average Citation"}, selected="total_cit")

                    # Reactive value to store cited countries results
                    cited_countries_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_cited_countries)
                    def cited_countries():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🌍 Analyzing most cited countries...",
                                "📊 Processing citation data by country...",
                                "🏆 Ranking countries by citations...",
                                "📈 Calculating citation metrics...",
                                "✨ Almost there! Preparing your dashboard...",
                                "🎯 Finalizing cited countries analysis...",
                                "🔗 Connecting citation and country data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            num_of_cited_countries = input.num_of_cited_countries()
                            cited_countries_measure = input.cited_countries()
                            result = get_cited_countries(df, num_of_cited_countries, cited_countries_measure)
                            cited_countries_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="most_cited_countries_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def show_cited_countries_placeholder():
                                result = cited_countries_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the Most Cited Countries analysis.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # When result is available, show the widget
                                return None
                            
                            @render_widget
                            def show_cited_countries():
                                result = cited_countries_results.get()
                                if result is not None:
                                    plot_cited_countries, _ = result
                                    return plot_cited_countries
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_cited_countries():
                                result = cited_countries_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the most cited countries data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, cited_countries_tab = result
                                return ui.HTML(DT(cited_countries_tab, style="width=100%;"))
        
        # --- Most Global Cited Documents Section ---
        with ui.nav_panel("None", value="most_global_cited_documents"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📄 Most Global Cited Documents", style="color: #5567BB;")
                    ui.p("The most global cited documents of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_cited_documents", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_global_cited_documents_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostGlobalCitedDocuments-{todaydate}.png"
                    )
                    def download_most_global_cited_documents():
                        plot_most_global_cited_documents, _ = cited_documents()
                        yield plotly_download(
                            plot_most_global_cited_documents,
                            title="Most Global Cited Documents",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.most_global_cited_documents_report)
                def show_most_global_cited_documents_report():
                    plots, most_global_cited_documents_tab = cited_documents()
                    report_excel.set(add_to_report(report_choices, report_excel, [most_global_cited_documents_tab], [plots], "mostglobcitdocs"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Most Global Cited Documents added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_global_cited_documents", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most global cited documents.")
                        ui.input_numeric("num_of_cited_docs", "Select the number of documents to apply to the dataset:", value=10)
                        ui.input_select("cited_docs", "Citation measure", {"total_cit": "Total Citations", "total_cit_per_year": "Total Citations per Year"}, selected="total_cit")

                    # Reactive value to store cited documents results
                    cited_documents_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_cited_documents)
                    def cited_documents():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "📄 Analyzing most global cited documents...",
                                "📊 Processing citation data by document...",
                                "🏆 Ranking documents by global citations...",
                                "📈 Calculating document citation metrics...",
                                "✨ Almost there! Preparing your dashboard...",
                                "🎯 Finalizing global cited documents analysis...",
                                "🔗 Connecting citation and document data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            num_of_cited_docs = input.num_of_cited_docs()
                            cited_docs = input.cited_docs()
                            result = get_cited_documents(df, num_of_cited_docs, cited_docs)
                            cited_documents_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="most_global_cited_documents_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def show_cited_documents_placeholder():
                                result = cited_documents_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the Most Global Cited Documents analysis.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                # When result is available, show the widget
                                return None
                            
                            @render_widget
                            def show_cited_documents():
                                result = cited_documents_results.get()
                                if result is not None:
                                    plot_cited_documents, _ = result
                                    return plot_cited_documents
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_cited_documents():
                                result = cited_documents_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the most global cited documents data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, cited_documents_tab = result
                                return ui.HTML(DT(cited_documents_tab, style="width=100%;"))
        
        # --- Most Local Cited Documents Section ---
        with ui.nav_panel("None", value="most_local_cited_documents"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📄 Most Local Cited Documents", style="color: #5567BB;")
                    ui.p("The most local cited documents of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_local_cited_documents", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_local_cited_documents_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostLocalCitedDocuments-{todaydate}.png"
                    )
                    def download_most_local_cited_documents():
                        result = local_cited_documents_results.get()
                        if result is not None:
                            plot_most_local_cited_documents, _ = result
                            yield plotly_download(
                                plot_most_local_cited_documents,
                                title="Most Local Cited Documents",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.most_local_cited_documents_report)
                def show_most_local_cited_documents_report():
                    result = local_cited_documents_results.get()
                    if result is not None:
                        plots, most_local_cited_documents_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [most_local_cited_documents_tab], [plots], "mostloccitdocs"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Most Local Cited Documents added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_local_cited_documents", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most local cited documents.")
                        ui.input_numeric("num_of_local_cited_docs", "Select the number of documents to apply to the dataset:", value=10)
                        ui.input_select("field_separator", "Field separator character", {"dot_comma": ";", "dot_dot": ":", "dot":"."}, selected="dot_comma")

                    # Initialize reactive value for storing results
                    local_cited_documents_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_local_cited_documents)
                    def run_local_cited_documents_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🔍 Processing local cited documents...",
                                "📊 Analyzing citation patterns...", 
                                "🌐 Generating document rankings...",
                                "📈 Computing citation metrics...",
                                "✨ Almost there! Preparing your dashboard...",
                                "🎯 Finalizing visualization...",
                                "🔗 Connecting citation and document data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis
                            num_of_local_cited_docs = input.num_of_local_cited_docs()
                            field_separator = input.field_separator()
                            result = get_local_cited_documents(df, num_of_local_cited_docs, field_separator)
                            local_cited_documents_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="most_local_cited_documents_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def placeholder_local_cited_documents():
                                result = local_cited_documents_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the most local cited documents plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return ""
                            
                            @render_widget
                            def show_local_cited_documents():
                                result = local_cited_documents_results.get()
                                if result is not None:
                                    plot_local_cited_documents, _ = result
                                    return plot_local_cited_documents
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_local_cited_documents():
                                result = local_cited_documents_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the most local cited documents data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, local_cited_documents_tab = result
                                return ui.HTML(DT(local_cited_documents_tab, style="width=100%;"))
        
        # --- Most Local Cited References Section ---
        with ui.nav_panel("None", value="most_local_cited_references"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📘 Most Local Cited References", style="color: #5567BB;")
                    ui.p("The most local cited references of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_local_cited_references", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_local_cited_references_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostLocalCitedReferences-{todaydate}.png"
                    )
                    def download_most_local_cited_references():
                        result = local_cited_refs_results.get()
                        if result is not None:
                            plot_most_local_cited_references, _ = result
                            yield plotly_download(
                                plot_most_local_cited_references,
                                title="Most Local Cited References",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.most_local_cited_references_report)
                def show_most_local_cited_references_report():
                    result = local_cited_refs_results.get()
                    if result is not None:
                        plots, most_local_cited_references_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [most_local_cited_references_tab], [plots], "mostloccitrefs"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Most Local Cited References added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_local_cited_references", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most local cited references.")
                        ui.input_numeric("num_of_cited_refs", "Select the number of references to apply to the dataset:", value=10)
                        ui.input_select("field_separator_ref", "Field separator character", {"dot_comma": ";", "dot_dot": ":", "dot":"."}, selected="dot_comma")

                    # Initialize reactive value for storing results
                    local_cited_refs_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_local_cited_references)
                    def run_local_cited_references_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🔍 Processing local cited references...",
                                "📊 Analyzing reference patterns...", 
                                "🌐 Generating reference rankings...",
                                "📈 Computing citation metrics...",
                                "✨ Almost there! Preparing your dashboard...",
                                "🎯 Finalizing visualization...",
                                "🔗 Connecting citation and reference data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis
                            num_of_cited_refs = input.num_of_cited_refs()
                            field_separator_ref = input.field_separator_ref()
                            result = get_local_cited_refs(df, num_of_cited_refs, field_separator_ref)
                            local_cited_refs_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="most_local_cited_references_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def placeholder_local_cited_refs():
                                result = local_cited_refs_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the most local cited references plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return ""
                            
                            @render_widget
                            def show_local_cited_refs():
                                result = local_cited_refs_results.get()
                                if result is not None:
                                    plot_local_cited_refs, _ = result
                                    return plot_local_cited_refs
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_local_cited_refs():
                                result = local_cited_refs_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the most local cited references data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, local_cited_refs_tab = result
                                return ui.HTML(DT(local_cited_refs_tab, style="width=100%;"))
        
        # --- References Spectroscopy Section ---
        with ui.nav_panel("None", value="references_spectroscopy"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📘 References Spectroscopy", style="color: #5567BB;")
                    ui.p("The references spectroscopy of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_references_spectroscopy", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("references_spectroscopy_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"ReferencesSpectroscopy-{todaydate}.png"
                    )
                    def download_references_spectroscopy():
                        result = ref_spectroscopy_results.get()
                        if result is not None:
                            plot_references_spectroscopy, _, _ = result
                            yield plotly_download(
                                plot_references_spectroscopy,
                                title="References Spectroscopy",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.references_spectroscopy_report)
                def show_references_spectroscopy_report():
                    result = ref_spectroscopy_results.get()
                    if result is not None:
                        plots, ref_rpy_tab, ref_spectroscopy_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [ref_rpy_tab, ref_spectroscopy_tab], [plots], "rpys"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ References Spectroscopy added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_references_spectroscopy", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the references spectroscopy.")
                        ui.input_select("field_separator_spec", "Field separator character", {";": ";", ",": ",", ".":"."}, selected="dot_comma")
                        with ui.layout_column_wrap(width=1 / 2):
                            ui.input_numeric("start_year", "Star Year", value=None)
                            current_year = datetime.now().year
                            ui.input_numeric("end_year", "EndYear", value=None)

                    # Initialize reactive value for storing results
                    ref_spectroscopy_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_references_spectroscopy)
                    def run_references_spectroscopy_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🔍 Processing references spectroscopy...",
                                "📊 Analyzing temporal patterns...", 
                                "🌐 Computing reference age distribution...",
                                "📈 Generating spectroscopy metrics...",
                                "✨ Almost there! Preparing your dashboard...",
                                "🎯 Finalizing visualization...",
                                "🔗 Connecting temporal and reference data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis
                            start_year = input.start_year()
                            end_year = input.end_year()
                            field_separator_spec = input.field_separator_spec()
                            result = get_references_spectroscopy(df, start_year, end_year, field_separator_spec)
                            ref_spectroscopy_results.set(result)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="references_spectroscopy_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def placeholder_references_spectroscopy():
                                result = ref_spectroscopy_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the references spectroscopy plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return ""
                            
                            @render_widget
                            def show_references_spectroscopy():
                                result = ref_spectroscopy_results.get()
                                if result is not None:
                                    plot_references_spectroscopy, _, _ = result
                                    return plot_references_spectroscopy
                        
                        with ui.nav_panel("Table - RPY"):
                            @render.ui
                            def table_references_rpy():
                                result = ref_spectroscopy_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the RPY data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, ref_rpy_tab, _ = result
                                return ui.HTML(DT(ref_rpy_tab, style="width=100%;"))

                        with ui.nav_panel("Table - Cited References"):
                            @render.ui
                            def table_references_spectroscopy():
                                result = ref_spectroscopy_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the cited references data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, _, ref_spectroscopy_tab = result
                                return ui.HTML(DT(ref_spectroscopy_tab, style="width=100%;"))

        # --- Most Frequent Words ---
        with ui.nav_panel("None", value="most_frequent_words"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🔑 Most Frequent Words", style="color: #5567BB;")
                    ui.p("The most frequent words in the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_frequent_words", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("most_frequent_words_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"MostFrequentWords-{todaydate}.png"
                    )
                    def download_most_frequent_words():
                        result = frequent_words_results.get()
                        if result is not None:
                            plot_most_frequent_words, _ = result
                            yield plotly_download(
                                plot_most_frequent_words,
                                title="Most Frequent Words",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.most_frequent_words_report)
                def show_most_frequent_words_report():
                    result = frequent_words_results.get()
                    if result is not None:
                        plots, most_frequent_words_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [most_frequent_words_tab], [plots], "mostfreqwords"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Most Frequent Words added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_most_frequent_words", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the most frequent words.")
                        ui.input_select("field_mfw", "Field", {"ID": "Keywords Plus", "DE": "Author's Keywords (DE)", "TI": "Titles", "AB": "Abstracts", "WC": "Subject Categories (WoS)"}, selected="ID")
                        
                        @render.express()
                        @reactive.event(input.field_mfw)
                        def get_frequent_ngrams():
                            if input.field_mfw() == "AB" or input.field_mfw() == "TI":
                                ui.input_select("ngram_mfw", "N-Grams", {1:"Unigrams", 2:"Bigrams", 3:"Trigrams"}, selected=1)

                        ui.input_numeric("num_of_words_mfw", "Number of words", value=10)

                        with ui.accordion(id="acc_mfw", open=False):
                            with ui.accordion_panel("Text Editing"):
                                ui.input_switch("remove_terms_mfw", "Load a list of terms to remove", value=False)
                                @render.express()
                                @reactive.event(input.remove_terms_mfw)
                                def get_frequent_ui():
                                    if input.remove_terms_mfw():
                                        ui.markdown("**Upload a TXT or CSV file containing a list of terms you want to remove from the analysis.** \nTerms have to be separated by a standard separator (comma, semicolon or tabulator).")
                                        ui.input_file("upload_terms_mfw", "", accept=[".txt", ".csv"])
                                        ui.input_select("terms_separator_mfw", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                                ui.input_switch("remove_synonyms_mfw", "Load a list of synonyms", value=False)
                                @render.express()
                                @reactive.event(input.remove_synonyms_mfw)
                                def get_synonyms_ui():
                                    if input.remove_synonyms_mfw():
                                        ui.markdown("**Upload a TXT or CSV file containing, in each row, a list of synonyms, that will be merged into a single term (the first word contained in the row).** \n Synonyms have to be separated by a standard separator (comma, semicolon or tabulator). Rows have to be separated by return separator.")
                                        ui.input_file("upload_synonyms_mfw", "", accept=[".txt", ".csv"])
                                        ui.input_select("synonyms_separator_mfw", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                    # Initialize reactive value for storing results
                    frequent_words_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_frequent_words)
                    def run_frequent_words_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🔍 Processing frequent words...",
                                "📊 Analyzing word patterns...", 
                                "🌐 Computing frequency metrics...",
                                "📈 Generating word rankings...",
                                "✨ Almost there! Preparing your dashboard...",
                                "🎯 Finalizing visualization...",
                                "🔗 Connecting word and frequency data...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            num_of_words_mfw = input.num_of_words_mfw()
                            field_mfw = input.field_mfw()
                            ngram_mfw = input.ngram_mfw() if field_mfw in ["AB", "TI"] else 1

                            file_upload_terms_mfw = None
                            file_upload_synonyms_mfw = None
                            terms_data_mfw = None
                            synonyms_data_mfw = None

                            if input.remove_terms_mfw():
                                file_upload_terms_mfw: list[FileInfo] | None = input.upload_terms_mfw()
                                if file_upload_terms_mfw:
                                    with open(file_upload_terms_mfw[0]['datapath'], 'r', encoding='utf-8') as file:
                                        terms_data_mfw = pd.DataFrame([line.strip() for line in file], columns=["Terms"])
                            else:
                                file_upload_terms_mfw = None
                                terms_data_mfw = None

                            if input.remove_synonyms_mfw():
                                file_upload_synonyms_mfw: list[FileInfo] | None = input.upload_synonyms_mfw()
                                if file_upload_synonyms_mfw:
                                    with open(file_upload_synonyms_mfw[0]['datapath'], 'r', encoding='utf-8') as file:
                                        synonyms_data_mfw = pd.DataFrame([line.strip() for line in file], columns=["Synonyms"])
                            else:
                                file_upload_synonyms_mfw = None
                                synonyms_data_mfw = None

                            result = get_frequent_words(df, ngram_mfw, num_of_words_mfw, field_mfw, file_upload_terms_mfw, file_upload_synonyms_mfw)
                            frequent_words_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()
                            
                        # Show additional modal for terms/synonyms if needed
                        modal_content_files = []
                        if terms_data_mfw is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Terms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(terms_data_mfw)))

                        if synonyms_data_mfw is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Synonyms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(synonyms_data_mfw)))

                        if modal_content_files:
                            modal = ui.modal(
                                *modal_content_files,
                                easy_close=True,
                                footer=ui.modal_button("Close", style="background: #5865B9; color: white")
                            )
                            ui.modal_show(modal)

                    with ui.navset_underline(id="most_frequent_words_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def placeholder_frequent_words():
                                result = frequent_words_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the most frequent words plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return ""
                            
                            @render_widget
                            def show_frequent_words():
                                result = frequent_words_results.get()
                                if result is not None:
                                    plot_frequent_words, _ = result
                                    return plot_frequent_words

                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_frequent_words():
                                result = frequent_words_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the most frequent words data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, frequent_words_tab = result
                                return ui.HTML(DT(frequent_words_tab, style="width=100%;"))
        
        # --- WordCloud Section ---
        with ui.nav_panel("None", value="wordcloud"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🔑 WordCloud", style="color: #5567BB;")
                    ui.p("The wordcloud of the most frequent words in the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_wordcloud", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("wordcloud_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"WordCloud-{todaydate}.png"
                    )
                    def download_wordcloud():
                        result = wordcloud_results.get()
                        if result is not None:
                            plot_wordcloud, _ = result
                            yield html_download(
                                plot_wordcloud,
                                title="WordCloud",
                                height=height.get(),
                                dpi=dpi.get(),
                            )

                @render.ui
                @reactive.event(input.wordcloud_report)
                def show_wordcloud_report():
                    result = wordcloud_results.get()
                    if result is not None:
                        plots, wordcloud_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [wordcloud_tab], [plots], "wordcloud"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ WordCloud added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_wordcloud", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the wordcloud.")
                        ui.input_select("field_wc", "Field", {"ID": "Keywords Plus", "DE": "Author's Keywords (DE)", "TI": "Titles", "AB": "Abstracts", "WC": "Subject Categories (WoS)"}, selected="ID")
                        
                        @render.express()
                        @reactive.event(input.field_wc)
                        def get_ngrams_wc():
                            if input.field_wc() == "AB" or input.field_wc() == "TI":
                                ui.input_select("ngram_wc", "N-Grams", {1:"Unigrams", 2:"Bigrams", 3:"Trigrams"}, selected=1)
                        
                        ui.input_numeric("num_of_words_wc", "Number of words", value=50)
                        
                        with ui.accordion(id="acc_wc", open=False):
                            with ui.accordion_panel("Text Editing"):
                                ui.input_switch("remove_terms_wc", "Load a list of terms to remove", value=False)
                                @render.express()
                                @reactive.event(input.remove_terms_wc)
                                def get_frequent_ngrams_wc():
                                    if input.remove_terms_wc():
                                        ui.markdown("**Upload a TXT or CSV file containing a list of terms you want to remove from the analysis.** \nTerms have to be separated by a standard separator (comma, semicolon or tabulator).")
                                        ui.input_file("upload_terms_wc", "", accept=[".txt", ".csv"])
                                        ui.input_select("terms_separator_wc", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                                ui.input_switch("remove_synonyms_wc", "Load a list of synonyms", value=False)
                                @render.express()
                                @reactive.event(input.remove_synonyms_wc)
                                def get_synonyms_wc():
                                    if input.remove_synonyms_wc():
                                        ui.markdown("**Upload a TXT or CSV file containing, in each row, a list of synonyms, that will be merged into a single term (the first word contained in the row).** \n Synonyms have to be separated by a standard separator (comma, semicolon or tabulator). Rows have to be separated by return separator.")
                                        ui.input_file("upload_synonyms_wc", "", accept=[".txt", ".csv"])
                                        ui.input_select("synonyms_separator_wc", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                    # Initialize reactive value for storing results
                    wordcloud_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_wordcloud)
                    def run_wordcloud_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🌫️ Generating your wordcloud...",
                                "🔍 Processing word frequencies...",
                                "🎨 Creating visual word representation...",
                                "📊 Calculating word weights...",
                                "✨ Almost there! Preparing your wordcloud...",
                                "🌐 Mapping word relationships...",
                                "🔗 Connecting words and frequencies...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            num_of_words_wc = input.num_of_words_wc()
                            field_wc = input.field_wc()
                            ngram_wc = input.ngram_wc() if field_wc in ["AB", "TI"] else 1

                            file_upload_terms_wc = None
                            file_upload_synonyms_wc = None
                            terms_data_wc = None
                            synonyms_data_wc = None

                            if input.remove_terms_wc():
                                file_upload_terms_wc: list[FileInfo] | None = input.upload_terms_wc()
                                if file_upload_terms_wc:
                                    with open(file_upload_terms_wc[0]['datapath'], 'r', encoding='utf-8') as file:
                                        terms_data_wc = pd.DataFrame([line.strip() for line in file], columns=["Terms"])
                            else:
                                file_upload_terms_wc = None
                                terms_data_wc = None

                            if input.remove_synonyms_wc():
                                file_upload_synonyms_wc: list[FileInfo] | None = input.upload_synonyms_wc()
                                if file_upload_synonyms_wc:
                                    with open(file_upload_synonyms_wc[0]['datapath'], 'r', encoding='utf-8') as file:
                                        synonyms_data_wc = pd.DataFrame([line.strip() for line in file], columns=["Synonyms"])
                            else:
                                file_upload_synonyms_wc = None
                                synonyms_data_wc = None

                            result = get_wordcloud(df, ngram_wc, num_of_words_wc, field_wc, file_upload_terms_wc, file_upload_synonyms_wc)
                            wordcloud_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()
                            
                        # Show additional modal for terms/synonyms if needed
                        modal_content_files = []
                        if terms_data_wc is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Terms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(terms_data_wc)))

                        if synonyms_data_wc is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Synonyms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(synonyms_data_wc)))

                        if modal_content_files:
                            modal_wc = ui.modal(
                                *modal_content_files,
                                easy_close=True,
                                footer=ui.modal_button("Close", style="background: #5865B9; color: white")
                            )
                            ui.modal_show(modal_wc)

                    with ui.navset_underline(id="wordcloud_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def placeholder_wordcloud():
                                result = wordcloud_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the wordcloud.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return ""
                            
                            @render.ui
                            def show_wordcloud():
                                result = wordcloud_results.get()
                                if result is not None:
                                    plot_wordcloud, _ = result
                                    return ui.HTML(f'<iframe src="{plot_wordcloud}" width="100%" height="800px" style="border:none;"></iframe>')

                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_wordcloud():
                                result = wordcloud_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the wordcloud data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, wordcloud_tab = result
                                return ui.HTML(DT(wordcloud_tab, style="width=100%;"))
        
        # --- TreeMap Section ---
        with ui.nav_panel("None", value="treemap"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🔑 TreeMap", style="color: #5567BB;")
                    ui.p("The treemap of the most frequent words in the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_treemap", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("treemap_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"TreeMap-{todaydate}.png"
                    )
                    def download_treemap():
                        result = treemap_results.get()
                        if result is not None:
                            plot_treemap, _ = result
                            yield plotly_download(
                                plot_treemap,
                                title="TreeMap",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.treemap_report)
                def show_treemap_report():
                    result = treemap_results.get()
                    if result is not None:
                        plots, treemap_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [treemap_tab], [plots], "treemap"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ TreeMap added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_treemap", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the treemap.")
                        ui.input_select("field_tm", "Field", {"ID": "Keywords Plus", "DE": "Author's Keywords (DE)", "TI": "Titles", "AB": "Abstracts", "WC": "Subject Categories (WoS)"}, selected="ID")
                        
                        @render.express()
                        @reactive.event(input.field_tm)
                        def get_ngrams_tm():
                            if input.field_tm() == "AB" or input.field_tm() == "TI":
                                ui.input_select("ngram_tm", "N-Grams", {1:"Unigrams", 2:"Bigrams", 3:"Trigrams"}, selected=1)
                        
                        ui.input_numeric("num_of_words_tm", "Number of words", value=50)
                        
                        with ui.accordion(id="acc_tm", open=False):
                            with ui.accordion_panel("Text Editing"):
                                ui.input_switch("remove_terms_tm", "Load a list of terms to remove", value=False)
                                @render.express()
                                @reactive.event(input.remove_terms_tm)
                                def get_frequent_ngrams_tm():
                                    if input.remove_terms_tm():
                                        ui.markdown("**Upload a TXT or CSV file containing a list of terms you want to remove from the analysis.** \nTerms have to be separated by a standard separator (comma, semicolon or tabulator).")
                                        ui.input_file("upload_terms_tm", "", accept=[".txt", ".csv"])
                                        ui.input_select("terms_separator_tm", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                                ui.input_switch("remove_synonyms_tm", "Load a list of synonyms", value=False)
                                @render.express()
                                @reactive.event(input.remove_synonyms_tm)
                                def get_synonyms_tm():
                                    if input.remove_synonyms_tm():
                                        ui.markdown("**Upload a TXT or CSV file containing, in each row, a list of synonyms, that will be merged into a single term (the first word contained in the row).** \n Synonyms have to be separated by a standard separator (comma, semicolon or tabulator). Rows have to be separated by return separator.")
                                        ui.input_file("upload_synonyms_tm", "", accept=[".txt", ".csv"])
                                        ui.input_select("synonyms_separator_tm", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                    # Initialize reactive value for storing results
                    treemap_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_treemap)
                    def run_treemap_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🌳 Building your treemap...",
                                "📊 Analyzing hierarchical data...",
                                "🔍 Processing word categories...",
                                "📈 Calculating size proportions...",
                                "✨ Almost there! Preparing your treemap...",
                                "🎨 Creating visual hierarchy...",
                                "🔗 Connecting data and visualization...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            num_of_words_tm = input.num_of_words_tm()
                            field_tm = input.field_tm()
                            ngram_tm = input.ngram_tm() if field_tm in ["AB", "TI"] else 1

                            file_upload_terms_tm = None
                            file_upload_synonyms_tm = None
                            terms_data_tm = None
                            synonyms_data_tm = None

                            if input.remove_terms_tm():
                                file_upload_terms_tm: list[FileInfo] | None = input.upload_terms_tm()
                                if file_upload_terms_tm:
                                    with open(file_upload_terms_tm[0]['datapath'], 'r', encoding='utf-8') as file:
                                        terms_data_tm = pd.DataFrame([line.strip() for line in file], columns=["Terms"])
                            else:
                                file_upload_terms_tm = None
                                terms_data_tm = None

                            if input.remove_synonyms_tm():
                                file_upload_synonyms_tm: list[FileInfo] | None = input.upload_synonyms_tm()
                                if file_upload_synonyms_tm:
                                    with open(file_upload_synonyms_tm[0]['datapath'], 'r', encoding='utf-8') as file:
                                        synonyms_data_tm = pd.DataFrame([line.strip() for line in file], columns=["Synonyms"])
                            else:
                                file_upload_synonyms_tm = None
                                synonyms_data_tm = None

                            result = get_treemap(df, ngram_tm, num_of_words_tm, field_tm, file_upload_terms_tm, file_upload_synonyms_tm)
                            treemap_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()
                            
                        # Show additional modal for terms/synonyms if needed
                        modal_content_files = []
                        if terms_data_tm is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Terms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(terms_data_tm)))

                        if synonyms_data_tm is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Synonyms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(synonyms_data_tm)))

                        if modal_content_files:
                            modal_tm = ui.modal(
                                *modal_content_files,
                                easy_close=True,
                                footer=ui.modal_button("Close", style="background: #5865B9; color: white")
                            )
                            ui.modal_show(modal_tm)

                    with ui.navset_underline(id="treemap_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def placeholder_treemap():
                                result = treemap_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the treemap plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return ""
                            
                            @render_widget
                            def show_treemap():
                                result = treemap_results.get()
                                if result is not None:
                                    plot_treemap, _ = result
                                    return plot_treemap

                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_treemap():
                                result = treemap_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the treemap data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, treemap_tab = result
                                return ui.HTML(DT(treemap_tab, style="width=100%;"))
        
        # --- References Spectroscopy Section ---
        with ui.nav_panel("None", value="words_frequency_over_time"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🔑 Words' Frequency over Time", style="color: #5567BB;")
                    ui.p("The trend of words' frequency over time in the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_words_frequency_over_time", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("words_frequency_over_time_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"WordsFrequencyOverTime-{todaydate}.png"
                    )
                    def download_words_frequency_over_time():
                        result = word_frequency_results.get()
                        if result is not None:
                            plot_words_frequency_over_time, _ = result
                            yield plotly_download(
                                plot_words_frequency_over_time,
                                title="Words Frequency Over Time",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.words_frequency_over_time_report)
                def show_words_frequency_over_time_report():
                    result = word_frequency_results.get()
                    if result is not None:
                        plots, words_frequency_over_time_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [words_frequency_over_time_tab], [plots], "wordfreqovertime"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Words Frequency Over Time added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_words_frequency", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the words' frequency over time.")
                        ui.input_select("field_wf", "Field", {"ID": "Keywords Plus", "DE": "Author's Keywords (DE)", "TI": "Titles", "AB": "Abstracts"}, selected="ID")
                        
                        @render.express()
                        @reactive.event(input.field_wf)
                        def get_ngrams_wf():
                            if input.field_wf() == "AB" or input.field_wf() == "TI":
                                ui.input_select("ngram_wf", "N-Grams", {1:"Unigrams", 2:"Bigrams", 3:"Trigrams"}, selected=1)
                        
                        with ui.accordion(id="acc_wf", multiple=True, open=False):
                            with ui.accordion_panel("Text Editing"):
                                ui.input_switch("remove_terms_wf", "Load a list of terms to remove", value=False)
                                @render.express()
                                @reactive.event(input.remove_terms_wf)
                                def get_frequent_ngrams_wf():
                                    if input.remove_terms_wf():
                                        ui.markdown("**Upload a TXT or CSV file containing a list of terms you want to remove from the analysis.** \nTerms have to be separated by a standard separator (comma, semicolon or tabulator).")
                                        ui.input_file("upload_terms_wf", "", accept=[".txt", ".csv"])
                                        ui.input_select("terms_separator_wf", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")
                                
                                ui.input_switch("remove_synonyms_wf", "Load a list of synonyms", value=False)
                                @render.express()
                                @reactive.event(input.remove_synonyms_wf)
                                def get_synonyms_wf():
                                    if input.remove_synonyms_wf():
                                        ui.markdown("**Upload a TXT or CSV file containing, in each row, a list of synonyms, that will be merged into a single term (the first word contained in the row).** \n Synonyms have to be separated by a standard separator (comma, semicolon or tabulator). Rows have to be separated by return separator.")
                                        ui.input_file("upload_synonyms_wf", "", accept=[".txt", ".csv"])
                                        ui.input_select("synonyms_separator_wf", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                            with ui.accordion_panel("Additional Options"):
                                ui.input_select('occurrences', 'Occurrences', {'cumulate': 'Cumulate', 'per_year': 'Per Year'}, selected='cumulate')
                                ui.input_slider('top_words', 'Number of words', min=1, max=100, value=[1, 10])

                    # Initialize reactive value for storing results
                    word_frequency_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_words_frequency_over_time)
                    def run_words_frequency_over_time_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "📈 Analyzing words frequency over time...",
                                "� Processing temporal word patterns...",
                                "📊 Computing frequency trends...",
                                "⏰ Tracking word evolution over time...",
                                "✨ Almost there! Preparing your analysis...",
                                "📉 Calculating temporal indicators...",
                                "🔗 Connecting words and time periods...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            field_wf = input.field_wf()
                            ngram_wf = input.ngram_wf() if field_wf in ["AB", "TI"] else 1
                            occurrences = input.occurrences()
                            top_words = input.top_words()

                            file_upload_terms_wf = None
                            file_upload_synonyms_wf = None
                            terms_data_wf = None
                            synonyms_data_wf = None

                            if input.remove_terms_wf():
                                file_upload_terms_wf: list[FileInfo] | None = input.upload_terms_wf()
                                if file_upload_terms_wf:
                                    with open(file_upload_terms_wf[0]['datapath'], 'r', encoding='utf-8') as file:
                                        terms_data_wf = pd.DataFrame([line.strip() for line in file], columns=["Terms"])
                            else:
                                file_upload_terms_wf = None
                                terms_data_wf = None

                            if input.remove_synonyms_wf():
                                file_upload_synonyms_wf: list[FileInfo] | None = input.upload_synonyms_wf()
                                if file_upload_synonyms_wf:
                                    with open(file_upload_synonyms_wf[0]['datapath'], 'r', encoding='utf-8') as file:
                                        synonyms_data_wf = pd.DataFrame([line.strip() for line in file], columns=["Synonyms"])
                            else:
                                file_upload_synonyms_wf = None
                                synonyms_data_wf = None

                            result = get_word_frequency(df, ngram_wf, field_wf, file_upload_terms_wf, file_upload_synonyms_wf, occurrences, top_words)
                            word_frequency_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()
                            
                        # Show additional modal for terms/synonyms if needed
                        modal_content_files = []
                        if terms_data_wf is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Terms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(terms_data_wf)))

                        if synonyms_data_wf is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Synonyms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(synonyms_data_wf)))

                        if modal_content_files:
                            modal_wf = ui.modal(
                                *modal_content_files,
                                easy_close=True,
                                footer=ui.modal_button("Close", style="background: #5865B9; color: white")
                            )
                            ui.modal_show(modal_wf)

                    with ui.navset_underline(id="words_frequency_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def placeholder_word_frequency():
                                result = word_frequency_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the words frequency over time plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return ""
                            
                            @render_widget
                            def show_word_frequency():
                                result = word_frequency_results.get()
                                if result is not None:
                                    plot_word_frequency, _ = result
                                    return plot_word_frequency

                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_word_frequency():
                                result = word_frequency_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the words frequency over time data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, word_frequency_tab = result
                                return ui.HTML(DT(word_frequency_tab, style="width:100%;"))
        
        # --- Trend Topics Section ---
        with ui.nav_panel("None", value="trend_topics"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🔑 Trend Topics", style="color: #5567BB;")
                    ui.p("The trend topics in the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_trend_topics", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("trend_topics_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"TrendTopics-{todaydate}.png"
                    )
                    def download_trend_topics():
                        result = trend_topics_results.get()
                        if result is not None:
                            plot_trend_topics, _ = result
                            yield plotly_download(
                                plot_trend_topics,
                                title="Trend Topics",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.trend_topics_report)
                def show_trend_topics_report():
                    result = trend_topics_results.get()
                    if result is not None:
                        plots, trend_topics_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [trend_topics_tab], [plots], "trendtopics"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Trend Topics added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_trend_topics", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the trend topics.")
                        ui.input_select("field_tt", "Field", {"ID": "Keywords Plus", "DE": "Author's Keywords (DE)", "TI": "Titles", "AB": "Abstracts"}, selected="ID")

                        @render.express()
                        @reactive.event(input.field_tt)
                        def get_ngrams_tt():
                            if input.field_tt() == "AB" or input.field_tt() == "TI":
                                ui.input_select("ngram_tt", "N-Grams", {1:"Unigrams", 2:"Bigrams", 3:"Trigrams"}, selected=1)
                                ui.input_select("stemming_tt", "Word Stemming", {True: "Yes", False: "No"}, selected=True)

                        @render.express()
                        def show_timespan():
                            data_temp = main_informations()
                            ui.input_slider("time_window", "Timespan", sep="", ticks=True, min=data_temp['Min_Year'][0], max=data_temp['Max_Year'][0], value=[data_temp['Min_Year'][0], data_temp['Max_Year'][0]], step=1, time_format="YYYY")

                        with ui.accordion(id="acc_tt", multiple=True, open=False):
                            with ui.accordion_panel("Text Editing"):
                                ui.input_switch("remove_terms_tt", "Load a list of terms to remove", value=False)
                                @render.express()
                                @reactive.event(input.remove_terms_tt)
                                def get_frequent_ngrams_tt():
                                    if input.remove_terms_tt():
                                        ui.markdown("**Upload a TXT or CSV file containing a list of terms you want to remove from the analysis.** \nTerms have to be separated by a standard separator (comma, semicolon or tabulator).")
                                        ui.input_file("upload_terms_tt", "", accept=[".txt", ".csv"])
                                        ui.input_select("terms_separator_tt", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                                ui.input_switch("remove_synonyms_tt", "Load a list of synonyms", value=False)
                                @render.express()
                                @reactive.event(input.remove_synonyms_tt)
                                def get_synonyms_tt():
                                    if input.remove_synonyms_tt():
                                        ui.markdown("**Upload a TXT or CSV file containing, in each row, a list of synonyms, that will be merged into a single term (the first word contained in the row).** \n Synonyms have to be separated by a standard separator (comma, semicolon or tabulator). Rows have to be separated by return separator.")
                                        ui.input_file("upload_synonyms_tt", "", accept=[".txt", ".csv"])
                                        ui.input_select("synonyms_separator_tt", "File Separator", {",":'Comma ","', ";": 'Semicolon ";"', "tab": "Tab"}, selected=",")

                            with ui.accordion_panel("Additional Options"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("word_mimimum_frequency", "Word Minimum Frequency", value=5)
                                    ui.input_numeric("number_of_words_year", "Number of Words per Year", value=3)

                    # Initialize reactive value for storing results
                    trend_topics_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_trend_topics)
                    def run_trend_topics_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "� Analyzing trend topics...",
                                "🔍 Processing topic evolution...",
                                "� Computing temporal patterns...",
                                "⏰ Tracking topic trends over time...",
                                "✨ Almost there! Preparing your analysis...",
                                "📉 Calculating topic indicators...",
                                "🔗 Connecting topics and time periods...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            field_tt = input.field_tt()
                            ngram_tt = input.ngram_tt() if field_tt in ["AB", "TI"] else 1
                            time_window = input.time_window()
                            
                            file_upload_terms_tt = None
                            file_upload_synonyms_tt = None
                            terms_data_tt = None
                            synonyms_data_tt = None

                            if input.remove_terms_tt():
                                file_upload_terms_tt: list[FileInfo] | None = input.upload_terms_tt()
                                if file_upload_terms_tt:
                                    with open(file_upload_terms_tt[0]['datapath'], 'r', encoding='utf-8') as file:
                                        terms_data_tt = pd.DataFrame([line.strip() for line in file], columns=["Terms"])
                            else:
                                file_upload_terms_tt = None
                                terms_data_tt = None

                            if input.remove_synonyms_tt():
                                file_upload_synonyms_tt: list[FileInfo] | None = input.upload_synonyms_tt()
                                if file_upload_synonyms_tt:
                                    with open(file_upload_synonyms_tt[0]['datapath'], 'r', encoding='utf-8') as file:
                                        synonyms_data_tt = pd.DataFrame([line.strip() for line in file], columns=["Synonyms"])
                            else:
                                file_upload_synonyms_tt = None
                                synonyms_data_tt = None

                            word_mimimum_frequency = input.word_mimimum_frequency()
                            number_of_words_year = input.number_of_words_year()

                            result = get_trend_topics(df, ngram_tt, field_tt, time_window, file_upload_terms_tt, file_upload_synonyms_tt, word_mimimum_frequency, number_of_words_year)
                            trend_topics_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()
                            
                        # Show additional modal for terms/synonyms if needed
                        modal_content_files = []
                        if terms_data_tt is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Terms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(terms_data_tt)))

                        if synonyms_data_tt is not None:
                            modal_content_files.append(ui.markdown("""<h3 style=\"text-align:center;\">Synonyms to Remove</h3>"""))
                            modal_content_files.append(ui.HTML(DT(synonyms_data_tt)))

                        if modal_content_files:
                            modal_tt = ui.modal(
                                *modal_content_files,
                                easy_close=True,
                                footer=ui.modal_button("Close", style="background: #5865B9; color: white")
                            )
                            ui.modal_show(modal_tt)

                    with ui.navset_underline(id="trend_topics_tab"):
                        with ui.nav_panel("Plot"):
                            @render.ui
                            def placeholder_trend_topics():
                                result = trend_topics_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the trend topics plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                return ""
                            
                            @render_widget
                            def show_trend_topics():
                                result = trend_topics_results.get()
                                if result is not None:
                                    plot_trend_topics, _ = result
                                    return plot_trend_topics

                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_trend_topics():
                                result = trend_topics_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the trend topics data table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="height: 400px; display: flex; flex-direction: column; justify-content: center; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                _, trend_topics_tab = result
                                return ui.HTML(DT(trend_topics_tab, style="width:100%;"))
        
        # --- Cluster Coupling ---
        with ui.nav_panel("None", value="cluster_analysis"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🔍 Cluster by Coupling", style="color: #5567BB;")
                    ui.p("The cluster analysis by coupling in the dataset")
                
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_cluster_analysis", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("cluster_analysis_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"ClusterAnalysis-{todaydate}.png"
                    )
                    def download_cluster_analysis():
                        result = clustering_coupling_results.get()
                        if result is not None:
                            plot_cluster_analysis, _, _, _ = result
                            yield plotly_download(
                                plot_cluster_analysis,
                                title="Cluster Analysis",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.cluster_analysis_report)
                def show_cluster_analysis_report():
                    result = clustering_coupling_results.get()
                    if result is not None:
                        plot_clustering_coupling, clustering_coupling_network, clustering_coupling_tab, clustering_coupling_clusters = result
                        report_excel.set(add_to_report(report_choices, report_excel, [clustering_coupling_tab, clustering_coupling_clusters], [plot_clustering_coupling, clustering_coupling_network], "couplingmap"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Cluster Analysis added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True): 
                with ui.layout_sidebar(fillable=True, fill=True):
                    with ui.sidebar(id="sidebar_cluster_analysis", position="right"):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the cluster analysis.")
                        ui.input_select("unit_of_analysis", "Unit of Analysis", {"documents": "Documents", "authors": "Authors", "sources": "Sources"}, selected="documents")
                        ui.input_select("coupling_field", "Coupling measured by", {"CR": "References", "ID": "Keywords Plus", "DE": "Author's Keywords (DE)", "TI": "Titles", "AB": "Abstracts"}, selected="CR")
                        
                        @render.express()
                        @reactive.event(input.coupling_field)
                        def get_stemmer_gc():
                            if input.coupling_field() == "AB" or input.coupling_field() == "TI":
                                ui.input_select("stemmer", "Word Stemming:", {True:"Yes", False:"No"}, selected=False)
                        
                        with ui.accordion(id="accordion_cluster_labeling", multiple=True, open=False):
                            with ui.accordion_panel("Impact Parameters"):    
                                ui.input_select("impact_measure", "Impact measure", {"local": "Local Citation Score", "global": "Global Citation Score"}, selected="local")
                                ui.input_select("cluster_labeling", "Cluster labeling by", {"none": "None", "ID": "Keywords Plus", "DE": "Author's Keywords (DE)", "TI": "Titles", "AB": "Abstracts"}, selected="ID")
                                
                                @render.express()
                                @reactive.event(input.cluster_labeling)
                                def get_ngrams_gc():
                                    if input.cluster_labeling() == "AB" or input.cluster_labeling() == "TI":
                                        ui.input_select("cl_ngram", "Select the n-gram to apply to the dataset:", {1:"Unigrams", 2:"Bigrams", 3:"Trigrams"}, selected=1)
                        
                            with ui.accordion_panel("Cluster Labeling Parameters"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("num_of_units", "Number of Units", value=250)
                                    ui.input_numeric("min_cluster_freq", "Min Cluster Freq.", value=5)    
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("label_per_cluster", "Label per cluster", value=3)
                                    ui.input_numeric("label_size", "Label size", value=0.3)
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("community_repulsion", "Community repulsion", value=0)
                                    ui.input_select("clustering_algorithm", "Clustering algorithm", {"none": "None", "edge_betweenness": "Edge Betweenness", "infomap": "InfoMap", "leading_eigen": "Leading Eigenvalues", "leiden": "Leiden", "louvain": "Louvain", "spinglass": "Spinglass", "walktrap": "Walktrap"}, selected="walktrap")

                    # Initialize reactive value for storing results
                    clustering_coupling_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_cluster_analysis)
                    def run_cluster_analysis_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "� Processing cluster by coupling...",
                                "📊 Computing coupling relationships...",
                                "🌐 Generating cluster structure...",
                                "📈 Optimizing community detection...",
                                "✨ Almost there! Preparing your network...",
                                "🎯 Finalizing network visualization...",
                                "🔗 Connecting documents and citations...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            unit_of_analysis = input.unit_of_analysis()
                            coupling_field = input.coupling_field()
                            stemmer = input.stemmer() if coupling_field in ["AB", "TI"] else False
                            impact_measure = input.impact_measure()
                            cluster_labeling = input.cluster_labeling()
                            ngram = input.cl_ngram() if cluster_labeling in ["AB", "TI"] else 1
                            num_of_units = input.num_of_units()
                            min_cluster_freq = input.min_cluster_freq()
                            label_per_cluster = input.label_per_cluster()
                            label_size = input.label_size()
                            community_repulsion = input.community_repulsion()
                            clustering_algorithm = input.clustering_algorithm()

                            result = get_clustering_coupling(df, unit_of_analysis, coupling_field, stemmer, impact_measure, cluster_labeling, ngram, num_of_units, min_cluster_freq, label_per_cluster, label_size, community_repulsion, clustering_algorithm)
                            clustering_coupling_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="clustering_coupling_tab"):
                        with ui.nav_panel("Map"):
                            @render.ui
                            def show_clustering_coupling_map():
                                result = clustering_coupling_results.get()
                                if result is not None:
                                    return None  # Hide placeholder when data is available
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run cluster by coupling", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                            @render_widget
                            def clustering_coupling_map_widget():
                                result = clustering_coupling_results.get()
                                if result is not None:
                                    plot_clustering_coupling, _, _, _ = result
                                    return plot_clustering_coupling
                                return None

                        with ui.nav_panel("Network"):
                            @render.ui
                            def network_clustering_coupling():
                                result = clustering_coupling_results.get()
                                if result is not None:
                                    _, clustering_coupling_network, _, _ = result
                                    return ui.HTML(f'<iframe src="{clustering_coupling_network}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run cluster by coupling", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_clustering_coupling():
                                result = clustering_coupling_results.get()
                                if result is not None:
                                    _, _, clustering_coupling_tab, _ = result
                                    return ui.HTML(DT(clustering_coupling_tab))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run cluster by coupling", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Clusters"):
                            @render.ui
                            def cluster_clustering_coupling():
                                result = clustering_coupling_results.get()
                                if result is not None:
                                    _, _, _, clustering_coupling_clusters = result
                                    return ui.HTML(DT(clustering_coupling_clusters))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run cluster by coupling", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                    # ui.busy_indicators.options(spinner_type="bars3")

                    # # Loader indicator
                    # @render.ui
                    # def indicator_types_ui_cluster():
                    #     return ui.busy_indicators.use(
                    #         spinners=input.go_clustering_coupling() > 0
                    #     )
        
        # --- Co-occurrence Network Section ---
        with ui.nav_panel("None", value="co_occurrence_network"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🔑 Co-occurrence Network", style="color: #5567BB;")
                    ui.p("The co-occurrence network in the dataset")
                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_co_occurrence_analysis", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("co_occurrence_network_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"CoOccurrenceNetwork-{todaydate}.png"
                    )
                    def download_co_occurrence_network():
                        result = co_occurrence_network_results.get()
                        if result is not None:
                            plot_co_occurrence_network, _, _, _ = result
                            yield html_download(
                                plot_co_occurrence_network,
                                title="Co-occurrence Network",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.co_occurrence_network_report)
                def show_co_occurrence_network_report():
                    result = co_occurrence_network_results.get()
                    if result is not None:
                        plot_co_occurrence_network, plot_density_plot, co_occurrence_network_tab, plot_degree_plot = result
                        report_excel.set(add_to_report(report_choices, report_excel, [co_occurrence_network_tab], [plot_co_occurrence_network, plot_density_plot, plot_degree_plot], "cowordnet"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Co-occurrence Network added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=True, fill=True):
                    # Sidebar for data import options
                    with ui.sidebar(id="sidebar_co_occurrence_network", position="right", ):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the co-occurrence network.")
                        ui.input_select("field_cn", "Field", {"ID": "Keywords Plus", "DE": "Author's Keywords (DE)", "TI": "Titles", "AB": "Abstracts"}, selected="ID")
                        
                        @render.express()
                        @reactive.event(input.field_cn)
                        def get_ngrams_co_occurrence():
                            if input.field_cn() == "AB" or input.field_cn() == "TI":
                                ui.input_select("cn_ngram", "Select the n-gram to apply to the dataset:", {1:"Unigrams", 2:"Bigrams", 3:"Trigrams"}, selected=1)
                        
                        with ui.accordion(id="accordion_co_occurrence_network", multiple=True, open=False):
                            with ui.accordion_panel("Text Editing Parameters"):
                                ui.input_switch("remove_terms_cn", "Remove terms", value=False)
                                @render.express()
                                @reactive.event(input.remove_terms_cn)
                                def get_frequent_ui_cn():
                                    if input.remove_terms_cn():
                                        ui.input_file("upload_terms", "Load a list of terms to remove", accept=[".txt", ".csv"])
                                
                                ui.input_switch("remove_synonyms_cn", "Remove punctuation", value=False)
                                @render.express()
                                @reactive.event(input.remove_synonyms_cn)
                                def get_synonyms_ui_cn():
                                    if input.remove_synonyms_cn():
                                        ui.input_file("upload_synonyms", "Load a list of synonyms to remove", accept=[".txt", ".csv"]) 
                        
                            with ui.accordion_panel("Network Parameters"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("network_layout", "Network Layout", {"auto": "Automatic layout", "fr": "Fruchterman-Reingold", "kk": "Kamada-Kawai", "circle": "Circle", "mdrl": "Multi Dimension Scaling", "graphopt": "Graphopt", "sphere": "Sphere", "star": "Star"}, selected="auto")
                                    ui.input_select("clustering_algorithm_cn", "Clustering Algorithm", {"none": "None", "edge_betweenness": "Edge Betweenness", "infomap": "InfoMap", "leading_eigen": "Leading Eigenvalues", "leiden": "Leiden", "louvain": "Louvain", "spinglass": "Spinglass", "walktrap": "Walktrap"}, selected="walktrap")
                                    ui.input_select("normalization_cn", "Normalization", {"association": "Association", "jaccard": "Jaccard", "inclusion": "Inclusion", "salton": "Salton", "equivalence": "Equivalence", "none": "None"}, selected="association")
                                    ui.input_switch("color_by_year", "Node Color by Year", value=False)

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("num_of_nodes", "Number of Nodes", value=50, min=10)
                                    ui.input_numeric("repulsion_force", "Repulsion Force", value=1, min=0, step=0.1)
                                    ui.input_switch("remove_isolated", "Remove Isolated Nodes", value=True)
                                    ui.input_numeric("min_edges", "Minimum Number of Edges", value=2, min=1)

                            with ui.accordion_panel("Graphical Parameters"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("node_opacity", "Node Opacity", value=0.7, min=0.1, max=1, step=0.05)
                                    ui.input_numeric("num_of_labels", "Number of Labels", value=1000, min=0)

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_switch("label_cex", "Label Cex", value=True)
                                    ui.input_select("node_shape", "Node Shape", {"circle": "Circle", "square": "Square", "dot": "Dot","ellipse": "Ellipse", "square": "Square", "text":"Text"}, selected="dot")

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("label_size_ls", "Label Size", value=3, min=0.1, step=0.1)
                                    ui.input_numeric("edge_size", "Edge Size", value=5, min=0.1, step=0.1)
                                    ui.input_switch("node_shadow", "Show Node Shadow", value=True)
                                    ui.input_switch("edit_nodes", "Enable Node Editing", value=False)

                    # Initialize reactive value for storing results
                    co_occurrence_network_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_co_occurrence_analysis)
                    def run_co_occurrence_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "�️ Processing co-occurrence network...",
                                "📊 Computing node relationships...",
                                "🌐 Building network structure...",
                                "📈 Optimizing layout algorithm...",
                                "✨ Almost there! Preparing your network...",
                                "🎯 Finalizing network visualization...",
                                "🔗 Connecting terms and concepts...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            field_cn = input.field_cn()
                            ngram_cn = input.cn_ngram() if field_cn in ["AB", "TI"] else 1
                            network_layout = input.network_layout()
                            clustering_algorithm_cn = input.clustering_algorithm_cn()
                            normalization_cn = input.normalization_cn()
                            color_by_year = input.color_by_year()
                            num_of_nodes = input.num_of_nodes()
                            repulsion_force = input.repulsion_force()
                            remove_isolated = input.remove_isolated()
                            min_edges = input.min_edges()
                            node_opacity = input.node_opacity()
                            num_of_labels = input.num_of_labels()
                            node_shape = input.node_shape()
                            label_size_ls = input.label_size_ls()
                            edge_size = input.edge_size()
                            node_shadow = input.node_shadow()
                            edit_nodes = input.edit_nodes()
                            label_cex = input.label_cex()

                            file_upload_terms = None
                            file_upload_synonyms = None
                            terms_data = None
                            synonyms_data = None

                            if input.remove_terms_cn():
                                file_upload_terms: list[FileInfo] | None = input.upload_terms()
                                if file_upload_terms:
                                    with open(file_upload_terms[0]['datapath'], 'r', encoding='utf-8') as file:
                                        terms_data = pd.DataFrame([line.strip() for line in file], columns=["Terms"])
                            else:
                                # Reset terms file if checkbox is disabled
                                file_upload_terms = None
                                terms_data = None

                            if input.remove_synonyms_cn():
                                file_upload_synonyms: list[FileInfo] | None = input.upload_synonyms()
                                if file_upload_synonyms:
                                    with open(file_upload_synonyms[0]['datapath'], 'r', encoding='utf-8') as file:
                                        synonyms_data = pd.DataFrame([line.strip() for line in file], columns=["Synonyms"])
                            else:
                                # Reset synonyms file if checkbox is disabled
                                file_upload_synonyms = None
                                synonyms_data = None

                            # Show modal for terms/synonyms if needed
                            modal_content = []

                            if terms_data is not None:
                                modal_content.append(ui.markdown("""<h3 style=\"text-align:center;\">Terms to Remove</h3>"""))
                                modal_content.append(ui.HTML(DT(terms_data)))

                            if synonyms_data is not None:
                                modal_content.append(ui.markdown("""<h3 style=\"text-align:center;\">Synonyms to Remove</h3>"""))
                                modal_content.append(ui.HTML(DT(synonyms_data)))

                            result = get_co_occurence_network(df, field_cn, ngram_cn, network_layout, clustering_algorithm_cn, normalization_cn, color_by_year, num_of_nodes, 
                                                            repulsion_force, remove_isolated, min_edges, node_opacity, num_of_labels, node_shape, label_size_ls,
                                                            edge_size, node_shadow, edit_nodes, label_cex, file_upload_terms, file_upload_synonyms)
                            co_occurrence_network_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()
                            
                        # Show modal for terms/synonyms after main processing if needed
                        if modal_content:
                            file_modal = ui.modal(
                                *modal_content,
                                easy_close=True,
                                footer=ui.modal_button("Close", style="background: #5865B9; color: white")
                            )
                            ui.modal_show(file_modal)

                    with ui.navset_underline(id="co_occurrence_network_tab"):
                        with ui.nav_panel("Network"):
                            @render.ui
                            def show_co_occurrence_network():
                                result = co_occurrence_network_results.get()
                                if result is not None:
                                    plot_co_occurrence_network, _, _, _ = result
                                    return ui.HTML(f'<iframe src="{plot_co_occurrence_network}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run co-occurrence network", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Density Plot"):
                            @render_widget
                            def density_plot_widget():
                                result = co_occurrence_network_results.get()
                                if result is not None:
                                    _, plot_density_plot, _, _ = result
                                    return plot_density_plot
                                return None
                            
                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_co_occurrence_network():
                                result = co_occurrence_network_results.get()
                                if result is not None:
                                    _, _, co_occurrence_network_tab, _ = result
                                    return ui.HTML(DT(co_occurrence_network_tab, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run co-occurrence network", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Degree Plot"):
                            @render_widget
                            def degree_plot_widget():
                                result = co_occurrence_network_results.get()
                                if result is not None:
                                    _, _, _, plot_degree_plot = result
                                    return plot_degree_plot
                                return None

        # --- Thematic Map Section ---
        with ui.nav_panel("None", value="thematic_map"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("🗺️ Thematic Map", style="color: #5567BB;")
                    ui.p("The thematic map of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_thematic_map_analysis", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("thematic_map_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"ThematicMap-{todaydate}.png"
                    )
                    def download_thematic_map():
                        result = thematic_map_results.get()
                        if result is not None:
                            plot_thematic_map, _, _, _, _ = result
                            yield plotly_download(
                                plot_thematic_map,
                                title="Thematic Map",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.thematic_map_report)
                def show_thematic_map_report():
                    result = thematic_map_results.get()
                    if result is not None:
                        plot_thematic_map, thematic_map_net, thematic_map_tab, thematic_map_clusters, thematic_map_docs = result
                        report_excel.set(add_to_report(report_choices, report_excel, [thematic_map_tab, thematic_map_clusters, thematic_map_docs], [plot_thematic_map, thematic_map_net], "thematicmap"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Thematic Map added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    with ui.sidebar(id="sidebar_thematic_map", position="right"):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the thematic map.")
                        ui.input_select("thematic_field", "Text source for analysis", {
                                        "ID": "Keywords Plus (ID)",
                                        "DE": "Author's Keywords (DE)",
                                        "TI": "Titles",
                                        "AB": "Abstracts"
                                    }, selected="ID")

                        @render.express()
                        @reactive.event(input.thematic_field)
                        def show_stemmer_input():
                            if input.thematic_field() in ["TI", "AB"]:
                                ui.input_select("thematic_stemmer", "Apply stemming?", {True: "Yes", False: "No"}, selected=False)

                        @render.express()
                        @reactive.event(input.thematic_field)
                        def show_ngram_input():
                            if input.thematic_field() in ["TI", "AB"]:
                                ui.input_select("thematic_ngram", "N-grams", {
                                    1: "Unigrams",
                                    2: "Bigrams",
                                    3: "Trigrams",
                                    4: "4-grams"
                                }, selected=1)

                        with ui.accordion(id="accordion_thematic_map", multiple=True, open=False):
                            with ui.accordion_panel("Text Editing Parameters"):
                                with ui.layout_column_wrap(width=1/2):
                                    ui.input_numeric("thematic_n", "Number of terms to include", value=250)
                                    ui.input_numeric("thematic_minfreq", "Minimum frequency", value=5)

                                with ui.layout_column_wrap(width=1/2):
                                    ui.input_numeric("thematic_label_size", "Label size", value=0.5)
                                    ui.input_numeric("thematic_n_labels", "Labels per cluster", value=1)

                        ui.input_select("thematic_clustering", "Clustering algorithm", {
                            "walktrap": "Walktrap",
                            "louvain": "Louvain",
                            "leiden": "Leiden",
                            "infomap": "Infomap"
                        }, selected="walktrap")

                        ui.input_numeric("thematic_repulsion", "Community repulsion", value=0.1)

                    # Initialize reactive value for storing results
                    thematic_map_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_thematic_map_analysis)
                    def run_thematic_map_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "�️ Processing thematic map...",
                                "📊 Computing keyword clusters...",
                                "🌐 Building thematic structure...",
                                "📈 Optimizing cluster positioning...",
                                "✨ Almost there! Preparing your map...",
                                "🎯 Finalizing thematic visualization...",
                                "🔗 Connecting themes and keywords...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            field = input.thematic_field()
                            stemming = input.thematic_stemmer() if field in ["TI", "AB"] else False
                            ngram = input.thematic_ngram() if field in ["TI", "AB"] else 1
                            n = input.thematic_n()
                            minfreq = input.thematic_minfreq()
                            label_size = input.thematic_label_size()
                            n_labels = input.thematic_n_labels()
                            cluster = input.thematic_clustering()
                            repulsion = input.thematic_repulsion()

                            result = get_thematic_map(df, field, n, minfreq, ngram, stemming,
                                                    label_size, n_labels, repulsion, cluster)
                            thematic_map_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()

                    with ui.navset_underline(id="thematic_tab"):
                        with ui.nav_panel("Map"):
                            @render.ui
                            def show_thematic_map():
                                result = thematic_map_results.get()
                                if result is not None:
                                    return None  # Hide placeholder when data is available
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run thematic map", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                            @render_widget
                            def thematic_map_widget():
                                result = thematic_map_results.get()
                                if result is not None:
                                    plot_map, _, _, _, _ = result
                                    return plot_map
                                return None

                        with ui.nav_panel("Network"):
                            @render.ui
                            def network_thematic_map():
                                result = thematic_map_results.get()
                                if result is not None:
                                    _, thematic_map_network, _, _, _ = result
                                    return ui.HTML(f'<iframe src="{thematic_map_network}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run thematic map", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Table"):
                            @render.ui
                            def table_thematic_map():
                                result = thematic_map_results.get()
                                if result is not None:
                                    _, _, thematic_map_table, _, _ = result
                                    return ui.HTML(DT(thematic_map_table, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run thematic map", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Clusters"):
                            @render.ui
                            def clusters_thematic_map():
                                result = thematic_map_results.get()
                                if result is not None:
                                    _, _, _, thematic_map_cluster, _ = result
                                    return ui.HTML(DT(thematic_map_cluster, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run thematic map", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                            
                        with ui.nav_panel("Documents"):
                            @render.ui
                            def documents_thematic_map():
                                result = thematic_map_results.get()
                                if result is not None:
                                    _, _, _, _, thematic_map_documents = result
                                    return ui.HTML(DT(thematic_map_documents, maxBytes="10MB", style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run thematic map", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
        
        # --- Thematic Evolution Section ---
        with ui.nav_panel("None", value="thematic_evolution"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📈 Thematic Evolution", style="color: #5567BB;")
                    ui.p("The thematic evolution of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_thematic_evolution_analysis", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("thematic_evolution_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"ThematicEvolution-{todaydate}.png"
                    )
                    def download_thematic_evolution():
                        result = thematic_evolution_results.get()
                        if result is not None:
                            plot_thematic_evolution, _, _ = result
                            yield html_download(
                                plot_thematic_evolution,
                                title="Thematic Evolution",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.thematic_evolution_report)
                def show_thematic_evolution_report():
                    result = thematic_evolution_results.get()
                    if result is not None:
                        plot_thematic_evolution, thematic_evolution_tab, TM = result
                        report_excel.set(add_to_report(report_choices, report_excel, [thematic_evolution_tab], [plot_thematic_evolution], "thematicevolution"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        for i in range(len(TM)):
                            report_excel.set(add_to_report(report_choices, report_excel, [TM[i]['words'], TM[i]['clusters'], TM[i]['documentToClusters']], [TM[i]['map'], TM[i]['net_html']], f"te_period_{i+1}"))
                            selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        
                        return ui.notification_show("✅ Thematic Evolution added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=True):
                    with ui.sidebar(id="sidebar_thematic_evolution", position="right"):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the thematic evolution.")
                        ui.input_select("thematic_evolution_field", "Text source for analysis", {
                            "ID": "Keywords Plus (ID)",
                            "DE": "Author's Keywords (DE)",
                            "TI": "Titles",
                            "AB": "Abstracts"
                        }, selected="ID")

                        ui.input_switch("overlap", "Avoid Label Overlap", value=True)

                        @render.express()
                        @reactive.event(input.thematic_evolution_field)
                        def show_text_editing_evolution():
                            if input.thematic_evolution_field() in ["TI", "AB"]:
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("thematic_evolution_stemmer", "Apply stemming?", {True: "Yes", False: "No"}, selected=False)
                                    ui.input_select("thematic_evolution_ngram", "N-grams", {
                                        1: "Unigrams",
                                        2: "Bigrams",
                                        3: "Trigrams",
                                        4: "4-grams"
                                    }, selected=1)

                        with ui.accordion(id="accordion_thematic_evolution", multiple=True, open=False):
                            with ui.accordion_panel("Text Editing Parameters"): 
                                ui.input_switch("remove_terms_te", "Remove terms", value=False)
                                    
                                @render.express()
                                @reactive.event(input.remove_terms_te)
                                def get_frequent_ngrams_te():
                                    if input.remove_terms_te():
                                        ui.input_file("upload_terms_te", "Load a list of terms to remove", accept=[".txt", ".csv"])

                                ui.input_switch("remove_synonyms_te", "Remove punctuation", value=False)

                                @render.express()
                                @reactive.event(input.remove_synonyms_te)
                                def get_synonyms_te():
                                    if input.remove_synonyms_te():
                                        ui.input_file("upload_synonyms_te", "Load a list of synonyms to remove", accept=[".txt", ".csv"])

                        
                            with ui.accordion_panel("Thematic Evolution Parameters"): 
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("thematic_evolution_n", "Number of terms to include", value=250)
                                    ui.input_numeric("thematic_evolution_minfreq", "Minimum frequency", value=5)

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("weight_index", "Weight Index", {
                                        "inc_index": "Inclusion Index",
                                        "inc_weight_word_occ": "Inclusion Index weighted by Word Occurrences",
                                        "stab_index": "Stability Index",
                                    }, selected="inc_weight_word_occ")
                                    ui.input_numeric("min_weight_index", "Minimum Weight Index", value=0.1, min=0.01, max=1.0, step=0.01)

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("thematic_evolution_label_size", "Label size", value=0.5)
                                    ui.input_numeric("thematic_evolution_n_labels", "Labels per cluster", value=1)

                                ui.input_select("thematic_evolution_clustering", "Clustering algorithm", {
                                    "walktrap": "Walktrap",
                                    "louvain": "Louvain",
                                    "leiden": "Leiden",
                                    "infomap": "Infomap"
                                }, selected="walktrap")

                        ui.markdown("Time Slices:")
                        with ui.layout_column_wrap(width=1 / 2):
                            ui.input_numeric("number_of_cutting_points", "Number of cutting points", value=1, min=1)

                            @render.express()
                            @reactive.event(input.number_of_cutting_points)
                            def get_cutting_years():
                                if input.number_of_cutting_points() > 1:
                                    for i in range(1, input.number_of_cutting_points()+1):
                                        value = 2019 - input.number_of_cutting_points() + i
                                        ui.input_numeric(f"cutting_year_{i}", f"Cutting Year {i}", value=value, min=1)
                                else:
                                    ui.input_numeric("cutting_year", "Cutting Year", value=2019, min=1)

                    # Initialize reactive value for storing results
                    thematic_evolution_results = reactive.Value(None)

                    @reactive.effect
                    @reactive.event(input.run_thematic_evolution_analysis)
                    def run_thematic_evolution_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "⏰ Processing thematic evolution...",
                                "📊 Computing temporal patterns...",
                                "🌐 Building evolution structure...",
                                "📈 Optimizing time periods...",
                                "✨ Almost there! Preparing your evolution...",
                                "🎯 Finalizing evolution visualization...",
                                "🔗 Connecting themes across time...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Run analysis with current parameters
                            field = input.thematic_evolution_field()
                            overlap = input.overlap()
                            n = input.thematic_evolution_n()
                            minfreq = input.thematic_evolution_minfreq()
                            weight_index = input.weight_index()
                            min_weight_index = input.min_weight_index()
                            label_size = input.thematic_evolution_label_size()
                            n_labels = input.thematic_evolution_n_labels()
                            cluster = input.thematic_evolution_clustering()

                            file_upload_terms_te = None
                            file_upload_synonyms_te = None
                            terms_data_te = None
                            synonyms_data_te = None

                            if input.remove_terms_te():
                                file_upload_terms_te: list[FileInfo] | None = input.upload_terms_te()
                                if file_upload_terms_te:
                                    with open(file_upload_terms_te[0]['datapath'], 'r', encoding='utf-8') as file:
                                        terms_data_te = pd.DataFrame([line.strip() for line in file], columns=["Terms"])
                            else:
                                # Reset terms file if checkbox is disabled
                                file_upload_terms_te = None
                                terms_data_te = None

                            if input.remove_synonyms_te():
                                file_upload_synonyms_te: list[FileInfo] | None = input.upload_synonyms_te()
                                if file_upload_synonyms_te:
                                    with open(file_upload_synonyms_te[0]['datapath'], 'r', encoding='utf-8') as file:
                                        synonyms_data_te = pd.DataFrame([line.strip() for line in file], columns=["Synonyms"])
                            else:
                                # Reset synonyms file if checkbox is disabled
                                file_upload_synonyms_te = None
                                synonyms_data_te = None

                            # Show modal for terms/synonyms if needed
                            modal_content_te = []

                            if terms_data_te is not None:
                                modal_content_te.append(ui.markdown("""<h3 style=\"text-align:center;\">Terms to Remove</h3>"""))
                                modal_content_te.append(ui.HTML(DT(terms_data_te)))

                            if synonyms_data_te is not None:
                                modal_content_te.append(ui.markdown("""<h3 style=\"text-align:center;\">Synonyms to Remove</h3>"""))
                                modal_content_te.append(ui.HTML(DT(synonyms_data_te)))

                            cutting_points = input.number_of_cutting_points() 

                            # Prepare arguments for get_thematic_evolution
                            # Build the list of cutting years for thematic evolution
                            if cutting_points == 1:
                                years = [input.cutting_year()]
                            elif cutting_points > 1:
                                years = []
                                for i in range(1, cutting_points+1):
                                    years.append(input[f"cutting_year_{i}"]())
                            else:
                                years = []

                            # Handle remove.terms and synonyms (if you want to support file upload for these)
                            remove_terms = terms_data_te["Terms"].tolist() if terms_data_te is not None else None
                            synonyms = synonyms_data_te["Synonyms"].tolist() if synonyms_data_te is not None else None

                            # ngrams and stemming: only for TI/AB
                            ngrams = input.thematic_evolution_ngram() if field in ["TI", "AB"] else 1
                            stemming = input.thematic_evolution_stemmer() if field in ["TI", "AB"] else False

                            result = get_thematic_evolution(df, field, years, n, weight_index, min_weight_index, minfreq, label_size, ngrams, stemming, n_labels, overlap, remove_terms, synonyms, cluster)
                            thematic_evolution_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()
                            
                        # Show modal for terms/synonyms after main processing if needed
                        if modal_content_te:
                            file_modal_te = ui.modal(
                                *modal_content_te,
                                easy_close=True,
                                footer=ui.modal_button("Close", style="background: #5865B9; color: white")
                            )
                            ui.modal_show(file_modal_te)
                    
                    @render.express()
                    @reactive.event(input.number_of_cutting_points)
                    def show_time_slices():
                        with ui.navset_underline(id="thematic_evolution_tab"):
                            with ui.nav_panel("Thematic Evolution"):
                                with ui.navset_underline(id="thematic_evolution_map_tab"):
                                    with ui.nav_panel("Map"):
                                        @render.ui
                                        def show_thematic_evolution_map():
                                            result = thematic_evolution_results.get()
                                            if result is not None:
                                                plot_map, _, _ = result
                                                return ui.HTML(f'<iframe src="{plot_map}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                            else:
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                                        
                                    with ui.nav_panel("Table"):
                                        @render.ui
                                        def table_thematic_evolution():
                                            result = thematic_evolution_results.get()
                                            if result is not None:
                                                _, thematic_evolution_table, _ = result
                                                return ui.HTML(DT(thematic_evolution_table, style="width=100%;"))
                                            else:
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                            if input.number_of_cutting_points() >= 0:
                                with ui.nav_panel("Time Slice 1"):
                                    with ui.navset_underline(id="thematic_evolution_map_tab_2"):
                                        with ui.nav_panel("Map"):
                                            @render_widget
                                            def show_thematic_evolution_map_2():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    return TM[0]["map"] if len(TM) > 0 else None
                                                return None
                                            
                                        with ui.nav_panel("Network"):
                                            @render.ui
                                            def network_thematic_evolution_2():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 0:
                                                        return ui.HTML(f'<iframe src="{TM[0]["net_html"]}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                                        
                                        with ui.nav_panel("Table"):
                                            @render.ui
                                            def table_thematic_evolution_2():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 0:
                                                        return ui.HTML(DT(TM[0]["words"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                                        
                                        with ui.nav_panel("Clusters"):
                                            @render.ui
                                            def clusters_thematic_evolution_2():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 0:
                                                        return ui.HTML(DT(TM[0]["clusters"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                                        
                                        with ui.nav_panel("Documents"):
                                            @render.ui
                                            def documents_thematic_evolution_2():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 0:
                                                        return ui.HTML(DT(TM[0]["documentToClusters"], maxBytes="10MB", style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                            if input.number_of_cutting_points() >= 1:
                                with ui.nav_panel("Time Slice 2"):
                                    with ui.navset_underline(id="thematic_evolution_map_tab_3"):
                                        with ui.nav_panel("Map"):
                                            @render_widget
                                            def show_thematic_evolution_map_3():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    return TM[1]["map"] if len(TM) > 1 else None
                                                return None
                                            
                                        with ui.nav_panel("Network"):
                                            @render.ui
                                            def network_thematic_evolution_3():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 1:
                                                        return ui.HTML(f'<iframe src="{TM[1]["net_html"]}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                                            
                                        with ui.nav_panel("Table"):
                                            @render.ui
                                            def table_thematic_evolution_3():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 1:
                                                        return ui.HTML(DT(TM[1]["words"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                                        with ui.nav_panel("Clusters"):
                                            @render.ui
                                            def clusters_thematic_evolution_3():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 1:
                                                        return ui.HTML(DT(TM[1]["clusters"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                                        with ui.nav_panel("Documents"):
                                            @render.ui
                                            def documents_thematic_evolution_3():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 1:
                                                        return ui.HTML(DT(TM[1]["documentToClusters"], maxBytes="10MB", style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                            
                            if input.number_of_cutting_points() >= 2:
                                with ui.nav_panel("Time Slice 3"):
                                    with ui.navset_underline(id="thematic_evolution_map_tab_4"):
                                        with ui.nav_panel("Map"):
                                            @render_widget
                                            def show_thematic_evolution_map_4():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    return TM[2]["map"] if len(TM) > 2 else None
                                                return None
                                            
                                        with ui.nav_panel("Network"):
                                            @render.ui
                                            def network_thematic_evolution_4():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 2:
                                                        return ui.HTML(f'<iframe src="{TM[2]["net_html"]}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                                            
                                        with ui.nav_panel("Table"):
                                            @render.ui
                                            def table_thematic_evolution_4():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 2:
                                                        return ui.HTML(DT(TM[2]["words"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                                        with ui.nav_panel("Clusters"):
                                            @render.ui
                                            def clusters_thematic_evolution_4():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 2:
                                                        return ui.HTML(DT(TM[2]["clusters"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                                        with ui.nav_panel("Documents"):
                                            @render.ui
                                            def documents_thematic_evolution_4():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 2:
                                                        return ui.HTML(DT(TM[2]["documentToClusters"], maxBytes="10MB", style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                            
                            if input.number_of_cutting_points() >= 3:
                                with ui.nav_panel("Time Slice 4"):
                                    with ui.navset_underline(id="thematic_evolution_map_tab_5"):
                                        with ui.nav_panel("Map"):
                                            @render_widget
                                            def show_thematic_evolution_map_5():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    return TM[3]["map"] if len(TM) > 3 else None
                                                return None
                                            
                                        with ui.nav_panel("Network"):
                                            @render.ui
                                            def network_thematic_evolution_5():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 3:
                                                        return ui.HTML(f'<iframe src="{TM[3]["net_html"]}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                                            
                                        with ui.nav_panel("Table"):
                                            @render.ui
                                            def table_thematic_evolution_5():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 3:
                                                        return ui.HTML(DT(TM[3]["words"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                                        with ui.nav_panel("Clusters"):
                                            @render.ui
                                            def clusters_thematic_evolution_5():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 3:
                                                        return ui.HTML(DT(TM[3]["clusters"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                                        with ui.nav_panel("Documents"):
                                            @render.ui
                                            def documents_thematic_evolution_5():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 3:
                                                        return ui.HTML(DT(TM[3]["documentToClusters"], maxBytes="10MB", style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                            if input.number_of_cutting_points() >= 4:
                                with ui.nav_panel("Time Slice 5"):
                                    with ui.navset_underline(id="thematic_evolution_map_tab_6"):
                                        with ui.nav_panel("Map"):
                                            @render_widget
                                            def show_thematic_evolution_map_6():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    return TM[4]["map"] if len(TM) > 4 else None
                                                return None
                                            
                                        with ui.nav_panel("Network"):
                                            @render.ui
                                            def network_thematic_evolution_6():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 4:
                                                        return ui.HTML(f'<iframe src="{TM[4]["net_html"]}" width="100%" frameborder="0" style="border:0; outline:none;"></iframe>')
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
                                            
                                        with ui.nav_panel("Table"):
                                            @render.ui
                                            def table_thematic_evolution_6():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 4:
                                                        return ui.HTML(DT(TM[4]["words"]), style="width=100%;")
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                                        with ui.nav_panel("Clusters"):
                                            @render.ui
                                            def clusters_thematic_evolution_6():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 4:
                                                        return ui.HTML(DT(TM[4]["clusters"], style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )

                                        with ui.nav_panel("Documents"):
                                            @render.ui
                                            def documents_thematic_evolution_6():
                                                result = thematic_evolution_results.get()
                                                if result is not None:
                                                    _, _, TM = result
                                                    if len(TM) > 4:
                                                        return ui.HTML(DT(TM[4]["documentToClusters"], maxBytes="10MB", style="width=100%;"))
                                                return ui.div(
                                                    ui.p("Click the Run Analysis button to run thematic evolution", style="text-align: center; color: #999; font-size: 16px;"),
                                                    style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                                )
        
        # --- Factorial Analysis Section ---
        with ui.nav_panel("None", value="factorial_analysis"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📊 Factorial Approach", style="color: #5567BB;")
                    ui.p("The factorial approach of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_factorial_analysis", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("factorial_analysis_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"FactorialAnalysis-{todaydate}.png"
                    )
                    def download_factorial_analysis():
                        result = factorial_analysis_results.get()
                        if result is not None:
                            plot_factorial_analysis, _, _, _ = result
                            yield plotly_download(
                                plot_factorial_analysis,
                                title="Factorial Analysis",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.factorial_analysis_report)
                def show_factorial_analysis_report():
                    result = factorial_analysis_results.get()
                    if result is not None:
                        plot_factorial_analysis, plot_dendogram, words_by_cluster, articles_by_cluster = result
                        report_excel.set(add_to_report(report_choices, report_excel, [words_by_cluster, articles_by_cluster], [plot_factorial_analysis, plot_dendogram], "factorialanalysis"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Factorial Analysis added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first", type="warning", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    with ui.sidebar(id="sidebar_factorial_approach", position="right"):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the factorial approach.")

                        # Accordion for Factorial Analysis parameters
                        with ui.accordion(id="accordion_factorial_analysis", multiple=True, open=False):
                            with ui.accordion_panel("Analysis Method & Text Field"):
                                # 1 — algoritmo di riduzione
                                ui.input_select(
                                    "wordmap_method",
                                    "Analysis Method",
                                    {
                                        "MCA": "Multiple Correspondence Analysis (MCA)",
                                        "CA":  "Correspondence Analysis (CA)",
                                        "MDS": "Multidimensional Scaling (MDS)",
                                    },
                                    selected="MCA",
                                )

                                # 2 — campo testuale da analizzare
                                ui.input_select(
                                    "wordmap_field",
                                    "Text Field",
                                    {
                                        "ID": "Keywords Plus (ID)",
                                        "DE": "Author's Keywords (DE)",
                                        "TI": "Titles",
                                        "AB": "Abstracts"
                                    },
                                    selected="ID",
                                )

                                @render.express()
                                @reactive.event(input.wordmap_method)
                                def get_ngrams_fa():
                                    if input.field_tt() == "AB" or input.field_tt() == "TI":
                                        ui.input_select("ngram_fa", "Select the n-gram to apply to the dataset:", {1:"Unigrams", 2:"Bigrams", 3:"Trigrams"}, selected=1)

                            with ui.accordion_panel("Basic Plot Settings"):
                                with ui.layout_column_wrap(width=1 / 3):
                                    ui.input_numeric("wordmap_dimX",  "X Axis Dimension",  value=0)
                                    ui.input_numeric("wordmap_dimY",  "Y Axis Dimension",  value=1)
                                    ui.input_numeric("wordmap_top_words", "Num. of terms", value=50)

                                ui.input_slider( "wordmap_threshold", "Label Overlap Threshold", min=0.01, max=1.0, value=0.10 )

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("wordmap_labelsize", "Label Font Size", value=16)
                                    ui.input_numeric("wordmap_dot_size",  "Base Dot Size", value=16)

                            with ui.accordion_panel("Analysis Parameters"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("wordmap_n_terms",    "Number of Terms",  value=50, min=10)
                                    ui.input_numeric("wordmap_n_clusters", "Number of Clusters", value=1, min=1)
                                    ui.input_numeric("wordmap_n_docs",     "Documents to Use (0 = all)", value=0, min=0)

                            with ui.accordion_panel("Text Editing"):
                                ui.input_switch("remove_terms_wm", "Remove terms", value=False)
                                
                                @render.express()
                                @reactive.event(input.remove_terms_wm)
                                def get_frequent_ngrams_wm():
                                    if input.remove_terms_wm():
                                        ui.input_file("upload_terms_wm", "Load a list of terms to remove", accept=[".txt", ".csv"])

                                ui.input_switch("remove_synonyms_wm", "Remove punctuation", value=False)

                                @render.express()
                                @reactive.event(input.remove_synonyms_wm)
                                def get_synonyms_wm():
                                    if input.remove_synonyms_wm():
                                        ui.input_file("upload_synonyms_wm", "Load a list of synonyms to remove", accept=[".txt", ".csv"])

                        # Initialize reactive value for storing results
                        factorial_analysis_results = reactive.Value(None)

                        @reactive.effect
                        @reactive.event(input.run_factorial_analysis)
                        def run_factorial_analysis():
                            # Show loading modal while calculating (same style as Sources Production over Time)
                            def loading_modal():
                                phrases = [
                                    "⏳ Loading... Please wait.",
                                    "� Processing factorial analysis...",
                                    "📊 Computing factor loadings...",
                                    "🌐 Building dimensional space...",
                                    "📈 Optimizing clustering algorithm...",
                                    "✨ Almost there! Preparing your analysis...",
                                    "🎯 Finalizing factorial visualization...",
                                    "🔗 Connecting words and dimensions...",
                                    "🌐 Exploring your scientific landscape...",
                                    "🚀 Science mapping in progress...",
                                ]
                                modal = ui.modal(
                                    ui.div(
                                        ui.img(
                                            src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                            height="150px",
                                            style="display: block; margin: 0 auto; text-align: center;",
                                        ),
                                        ui.h4(
                                            phrases[0],
                                            id="loading-phrase",
                                            style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                        ),
                                    ),
                                    easy_close=False,
                                    footer=None,
                                )
                                js = f"""
                                <script>
                                (function() {{
                                    var phrases = {phrases};
                                    var idx = 0;
                                    var el = document.getElementById('loading-phrase');
                                    if (el) {{
                                        setInterval(function() {{
                                            idx = (idx + 1) % phrases.length;
                                            el.textContent = phrases[idx];
                                        }}, 1000);
                                    }}
                                }})();
                                </script>
                                """
                                return ui.HTML(str(modal) + js)
                            
                            ui.modal_show(loading_modal())
                            try:
                                # Run analysis with current parameters
                                field = input.wordmap_field()
                                ngram = input.ngram_fa() if field in ["TI", "AB"] else 1

                                file_upload_terms_wm = None
                                file_upload_synonyms_wm = None
                                terms_data_wm = None
                                synonyms_data_wm = None

                                if input.remove_terms_wm():
                                    file_upload_terms_wm: list[FileInfo] | None = input.upload_terms_wm()
                                    if file_upload_terms_wm:
                                        with open(file_upload_terms_wm[0]['datapath'], 'r', encoding='utf-8') as file:
                                            terms_data_wm = pd.DataFrame([line.strip() for line in file], columns=["Terms"])
                                else:
                                    # Reset terms file if checkbox is disabled
                                    file_upload_terms_wm = None
                                    terms_data_wm = None

                                if input.remove_synonyms_wm():
                                    file_upload_synonyms_wm: list[FileInfo] | None = input.upload_synonyms_wm()
                                    if file_upload_synonyms_wm:
                                        with open(file_upload_synonyms_wm[0]['datapath'], 'r', encoding='utf-8') as file:
                                            synonyms_data_wm = pd.DataFrame([line.strip() for line in file], columns=["Synonyms"])
                                else:
                                    # Reset synonyms file if checkbox is disabled
                                    file_upload_synonyms_wm = None
                                    synonyms_data_wm = None

                                # Show modal for terms/synonyms if needed
                                modal_content_wm = []

                                if terms_data_wm is not None:
                                    modal_content_wm.append(ui.markdown("""<h3 style=\"text-align:center;\">Terms to Remove</h3>"""))
                                    modal_content_wm.append(ui.HTML(DT(terms_data_wm)))

                                if synonyms_data_wm is not None:
                                    modal_content_wm.append(ui.markdown("""<h3 style=\"text-align:center;\">Synonyms to Remove</h3>"""))
                                    modal_content_wm.append(ui.HTML(DT(synonyms_data_wm)))

                                n_terms=input.wordmap_n_terms()
                                n_clusters=input.wordmap_n_clusters()
                                num_documents=(input.wordmap_n_docs() or None)
                                method=input.wordmap_method()
                                dimX=input.wordmap_dimX()
                                dimY=input.wordmap_dimY()
                                topWordPlot=input.wordmap_top_words()
                                threshold=input.wordmap_threshold()
                                labelsize=input.wordmap_labelsize()
                                size=input.wordmap_dot_size()

                                result = get_factorial_analysis(df, ngram, field, terms_data_wm, synonyms_data_wm, n_terms, n_clusters, num_documents, method, dimX, dimY, topWordPlot, threshold, labelsize, size)
                                factorial_analysis_results.set(result)
                            except Exception as e:
                                ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                            finally:
                                ui.modal_remove()
                                
                            # Show modal for terms/synonyms after main processing if needed
                            if modal_content_wm:
                                file_modal_wm = ui.modal(
                                    *modal_content_wm,
                                    easy_close=True,
                                    footer=ui.modal_button("Close", style="background: #5865B9; color: white")
                                )
                                ui.modal_show(file_modal_wm)
                    
                    with ui.navset_underline():
                        with ui.nav_panel("Word Map"):
                            @render.ui
                            def show_word_map_placeholder():
                                result = factorial_analysis_results.get()
                                if result is not None:
                                    return None  # Hide placeholder when data is available
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run factorial analysis", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                            @render_widget
                            def word_map_widget():
                                result = factorial_analysis_results.get()
                                if result is not None:
                                    plot_word_map, _, _, _ = result
                                    return plot_word_map
                                return None
                            
                        with ui.nav_panel("Topic Dendrogram"):
                            @render.ui
                            def show_topic_dendrogram():
                                result = factorial_analysis_results.get()
                                if result is not None:
                                    _, plot_dendrogram, _, _ = result
                                    return ui.HTML(f'<iframe src="/{plot_dendrogram}" width="100%" height="800px" style="border:none;"></iframe>')
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run factorial analysis", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                            
                        with ui.nav_panel("Words by Cluster"):
                            @render.ui
                            def show_words_by_cluster():
                                result = factorial_analysis_results.get()
                                if result is not None:
                                    _, _, words_by_cluster, _ = result
                                    return ui.HTML(DT(words_by_cluster, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run factorial analysis", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                            
                        with ui.nav_panel("Articles by Cluster"):
                            @render.ui
                            def show_articles_by_cluster():
                                result = factorial_analysis_results.get()
                                if result is not None:
                                    _, _, _, articles_by_cluster = result
                                    return ui.HTML(DT(articles_by_cluster, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to run factorial analysis", style="text-align: center; color: #999; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
        
        # --- Co-citation Network Section ---
        with ui.nav_panel("None", value="co-citation-network"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📊 Co-citation Network", style="color: #5567BB;")
                    ui.p("The co-citation network of the dataset")
                    
                    # Reactive value to store analysis results
                    co_citation_results = reactive.Value(None)

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_co_citation_network", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("co_citation_network_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"CoCitationNetwork-{todaydate}.png"
                    )
                    def download_co_citation_network():
                        plot_co_citation_network, _, _, _ = co_citation_network_results.get()
                        yield html_download(
                            plot_co_citation_network,
                            title="Co-Citation Network",
                            height=height.get(),
                            dpi=dpi.get()
                        )

                @render.ui
                @reactive.event(input.co_citation_network_report)
                def show_co_citation_network_report():
                    co_citation_net, density_plot, co_citation_tab, degree_plot = co_citation_network_results.get()
                    report_excel.set(add_to_report(report_choices, report_excel, [co_citation_tab], [co_citation_net, density_plot, degree_plot], "cocitnet"))
                    selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                    return ui.notification_show("✅ Co-Citation Network added to report", duration=5, close_button=False)

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=True):
                    # Initialize reactive values for results
                    co_citation_network_results = reactive.Value(None)
                    
                    @reactive.effect
                    @reactive.event(input.run_co_citation_network)
                    def run_co_citation_network_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🔗 Processing co-citation network...",
                                "📊 Analyzing citations relationships...",
                                "🌐 Building citation network structure...",
                                "📈 Computing network layouts...",
                                "✨ Almost there! Preparing your network...",
                                "🎯 Finalizing network visualization...",
                                "🔗 Connecting citations and references...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Get parameters
                            field = input.co_citation_field()
                            sep = input.citSep()
                            cocit_network_layout = input.cocit_network_layout()
                            cocit_clustering_algorithm = input.cocit_clustering_algorithm()
                            cocit_repulsion = input.cocit_repulsion()
                            cocit_shape = input.cocit_shape()
                            cocit_shadow = input.cocit_shadow()
                            cocit_curved = input.cocit_curved()
                            citlabelsize = input.citlabelsize()
                            citedgesize = input.citedgesize()
                            citlabel_cex = input.citlabel_cex()
                            citNodes = input.citNodes()
                            cit_isolates = input.cit_isolates()
                            citedges_min = input.citedges_min()
                            
                            # Execute analysis
                            result = get_co_citation(
                                df=df,
                                field=field,
                                sep=sep,
                                cocit_network_layout=cocit_network_layout,
                                cocit_clustering_algorithm=cocit_clustering_algorithm,
                                cocit_repulsion=cocit_repulsion,
                                cocit_shape=cocit_shape,
                                cocit_shadow=cocit_shadow,
                                cocit_curved=cocit_curved,
                                citlabelsize=citlabelsize,
                                citedgesize=citedgesize,
                                citlabel_cex=citlabel_cex,
                                citNodes=citNodes,
                                cit_isolates=cit_isolates,
                                citedges_min=citedges_min
                            )
                            
                            # Store results
                            co_citation_network_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()

                    with ui.sidebar(id="sidebar_co_citation_network", position="right"):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the co-citation network.")
                        ui.input_select("co_citation_field", "Field",
                            {
                                "CR": "Papers",
                                "CR_AU": "Authors",
                                "CR_SO": "Sources"
                            },
                            selected="CR"
                        )
                        ui.input_select("citSep", "Field separator character",
                            {
                                ";": '";" (Semicolon)',
                                ".   ": '".   " (Dot and 3 or more spaces)',
                                ",": '"," (Comma)'
                            },
                            selected=";"
                        )

                        with ui.accordion(id="accordion_co_citation_network", multiple=True, open=False):
                            with ui.accordion_panel("Method Parameters"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("cocit_network_layout", "Network Layout", {"auto": "Automatic layout", "fr": "Fruchterman-Reingold", "kk": "Kamada-Kawai", "circle": "Circle", "mdrl": "Multi Dimension Scaling", "graphopt": "Graphopt", "sphere": "Sphere", "star": "Star"}, selected="auto")
                                    ui.input_select("cocit_clustering_algorithm", "Clustering Algorithm", {"none": "None", "edge_betweenness": "Edge Betweenness", "infomap": "InfoMap", "leading_eigen": "Leading Eigenvalues", "leiden": "Leiden", "louvain": "Louvain", "spinglass": "Spinglass", "walktrap": "Walktrap"}, selected="walktrap")

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("citNodes", "Number of Nodes", min=5, max=1000, value=50, step=1)
                                    ui.input_numeric("cocit_repulsion", "Repulsion Force", min=0, max=1, value=0.1, step=0.1)

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("cit_isolates", "Remove Isolated Nodes", {"yes": "Yes", "no": "No"}, selected="yes")
                                    ui.input_numeric("citedges_min", "Minimum Number of Edges", value=2, step=1, min=0)

                            with ui.accordion_panel("Graphical Parameters"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select(
                                        "citShortlabel",
                                        "Short Label",
                                        {"Yes": "Yes", "No": "No"},
                                        selected="Yes"
                                    )
                                    ui.input_numeric(
                                        "citLabels",
                                        "Number of labels",
                                        min=0,
                                        max=1000,
                                        value=1000,
                                        step=1
                                    )
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select(
                                        "citlabel_cex",
                                        "Label cex",
                                        {"Yes": "Yes", "No": "No"},
                                        selected="Yes"
                                    )
                                    ui.input_select(
                                        "cocit_shape",
                                        "Node Shape",
                                        {
                                            "box": "Box",
                                            "circle": "Circle",
                                            "dot": "Dot",
                                            "ellipse": "Ellipse",
                                            "square": "Square",
                                            "text": "Text"
                                        },
                                        selected="dot"
                                    )
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric(
                                        "citlabelsize",
                                        "Label size",
                                        min=0.0,
                                        max=20,
                                        value=2,
                                        step=0.10
                                    )
                                    ui.input_numeric(
                                        "citedgesize",
                                        "Edge size",
                                        min=0.5,
                                        max=20,
                                        value=2,
                                        step=0.5
                                    )
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select(
                                        "cocit_shadow",
                                        "Node shadow",
                                        {"Yes": "Yes", "No": "No"},
                                        selected="Yes"
                                    )
                                    ui.input_select(
                                        "cocit_curved",
                                        "Edit Nodes",
                                        {"Yes": "Yes", "No": "No"},
                                        selected="No"
                                    )

                    with ui.navset_underline():
                        with ui.nav_panel("Network"):
                            @render.ui
                            def show_cocitation_network():
                                result = co_citation_network_results.get()
                                if result is not None:
                                    plot_cocit, _, _, _ = result
                                    return ui.HTML(f'<iframe src="{plot_cocit}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the co-citation network.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                            
                            
                        with ui.nav_panel("Density"):
                            @render_widget
                            def show_cocitation_density_table():
                                result = co_citation_network_results.get()
                                if result is not None:
                                    _, density_plot, _, _ = result
                                    return density_plot
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the density plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                            
                        with ui.nav_panel("Table"):
                            @render.ui
                            def show_cocitation_table():
                                result = co_citation_network_results.get()
                                if result is not None:
                                    _, _, cocit_table, _ = result
                                    return ui.HTML(DT(cocit_table, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the co-citation table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Degree Plot"):
                            @render_widget
                            def show_cocitation_clusters():
                                result = co_citation_network_results.get()
                                if result is not None:
                                    _, _, _, degree_plot = result
                                    return degree_plot
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the degree plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

        # --- Historiograph Section ---
        with ui.nav_panel("None", value="historiograph"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📊 Historiograph", style="color: #5567BB;")
                    ui.p("The historiograph of the dataset")
                    
                    # Reactive value to store analysis results
                    historiograph_results = reactive.Value(None)

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_historiograph", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("historiograph_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"Historiograph-{todaydate}.png"
                    )
                    def download_historiograph():
                        result = historiograph_results.get()
                        if result is not None:
                            _, _, plot_historiograph = result
                            yield html_download(
                                plot_historiograph,
                                title="Historiograph",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.historiograph_report)
                def show_historiograph_report():
                    result = historiograph_results.get()
                    if result is not None:
                        _, historiograph_tab, historiograph_net = result
                        report_excel.set(add_to_report(report_choices, report_excel, [historiograph_tab], [historiograph_net], "historiograph"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Historiograph added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first by clicking the Run Analysis button", duration=5, close_button=False, type="warning")

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=True):
                    # Initialize reactive values for results
                    historiograph_results = reactive.Value(None)
                    
                    @reactive.effect
                    @reactive.event(input.run_historiograph)
                    def run_historiograph_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "📚 Processing historiograph...",
                                "📊 Analyzing citation chronology...",
                                "🌐 Building historical network...",
                                "📈 Computing temporal layouts...",
                                "✨ Almost there! Preparing your timeline...",
                                "🎯 Finalizing historical visualization...",
                                "🔗 Connecting historical citations...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Get parameters
                            histNodes = input.histNodes()
                            histlabelsize = input.histlabelsize()
                            histsize = input.histsize()
                            # Execute analysis with correct parameters
                            result = get_historiograph(
                                df=df,
                                node_label="AU1",
                                histNodes=histNodes,
                                hist_isolates=True,
                                histlabelsize=histlabelsize,
                                histsize=histsize,
                                sep=";"
                            )
                            
                            # Store results
                            historiograph_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()

                    with ui.sidebar(id="sidebar_historiograph", position="right"):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the historiograph.")
                        ui.input_numeric(
                            "histNodes",
                            "Number of Nodes",
                            min=5,
                            max=100,
                            value=20,
                            step=1
                        )

                        ui.markdown("**Graphical Parameters**")
                        ui.input_select(
                            "titlelabel",
                            "Node label",
                            {
                                "AU1": "Short id (1st Author, Year)",
                                "TI": "Document Title",
                                "ID": "Authors' Keywords",
                                "DE": "Keywords Plus"
                            },
                            selected="AU1"
                        )

                        ui.input_select(
                            "hist_isolates",
                            "Remove Isolated Nodes",
                            {"True": "Yes", "False": "No"},
                            selected="True"
                        )

                        with ui.layout_column_wrap(width=1/2):
                            ui.input_numeric(
                                "histlabelsize",
                                "Label size",
                                min=0.0,
                                max=20,
                                value=20,
                                step=1
                            )
                            ui.input_numeric(
                                "histsize",
                                "Node size",
                                min=0,
                                max=20,
                                value=20,
                                step=1
                            )

                    with ui.navset_underline():
                        with ui.nav_panel("Network"):
                            @render.ui
                            def show_hist_network():
                                result = historiograph_results.get()
                                if result is not None:
                                    _, _, html_path = result
                                    return ui.HTML(f'<iframe src="/{html_path}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the historiograph network.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Table"):
                            @render.ui
                            def show_hist_table():
                                result = historiograph_results.get()
                                if result is not None:
                                    _, hist_tab, _ = result
                                    return ui.HTML(DT(hist_tab, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the historiograph table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

        # --- Collaboration Network Section ---
        with ui.nav_panel("None", value="collaboration_network"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📊 Collaboration Network", style="color: #5567BB;")
                    ui.p("The collaboration network of the dataset")
                    
                    # Reactive value to store analysis results
                    collaboration_network_results = reactive.Value(None)

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_collaboration_network", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("collaboration_network_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"CollaborationNetwork-{todaydate}.png"
                    )
                    def download_collaboration_network():
                        result = collaboration_network_results.get()
                        if result is not None:
                            plot_collaboration_network, _, _, _ = result
                            yield html_download(
                                plot_collaboration_network,
                                title="Collaboration Network",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.collaboration_network_report)
                def show_collaboration_network_report():
                    result = collaboration_network_results.get()
                    if result is not None:
                        collaboration_net, collaboration_density_plot, collaboration_network_tab, collaboration_degree_plot = result
                        report_excel.set(add_to_report(report_choices, report_excel, [collaboration_network_tab], [collaboration_net, collaboration_density_plot, collaboration_degree_plot], "collabnet"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Collaboration Network added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first by clicking the Run Analysis button", duration=5, close_button=False, type="warning")

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Initialize reactive values for results
                    collaboration_network_results = reactive.Value(None)
                    
                    @reactive.effect
                    @reactive.event(input.run_collaboration_network)
                    def run_collaboration_network_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🤝 Processing collaboration network...",
                                "📊 Analyzing research collaborations...",
                                "🌐 Building collaboration structure...",
                                "📈 Computing network layouts...",
                                "✨ Almost there! Preparing your network...",
                                "🎯 Finalizing collaboration visualization...",
                                "🔗 Connecting authors and institutions...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Get parameters
                            field = input.collab_field()
                            network_layout = input.collab_network_layout()
                            clustering_algorithm = input.collab_clustering_algorithm()
                            repulsion = input.collab_repulsion()
                            shape = input.collab_shape()
                            # Set default values for missing parameters
                            opacity = 1.0
                            shadow = "Yes"
                            curved = "No"
                            colnormalize = "none"
                            labelsize = 2.0
                            edgesize = 2.0
                            label_cex = "Yes"
                            nodes = 50
                            isolates = "yes"
                            edges_min = 2
                            
                            # Execute analysis
                            result = get_collaboration_network(
                                df=df,
                                field=field,
                                network_layout=network_layout,
                                clustering_algorithm=clustering_algorithm,
                                repulsion=repulsion,
                                shape=shape,
                                opacity=opacity,
                                shadow=shadow,
                                curved=curved,
                                colnormalize=colnormalize,
                                labelsize=labelsize,
                                edgesize=edgesize,
                                label_cex=label_cex,
                                nodes=nodes,
                                isolates=isolates,
                                edges_min=edges_min
                            )
                            
                            # Store results
                            collaboration_network_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()

                    with ui.sidebar(id="sidebar_collaboration_network", position="right"):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the collaboration network.")
                        ui.input_select("collab_field", "Field",
                            {
                                "COL_AU": "Authors",
                                "COL_UN": "Institutions",
                                "COL_CO": "Countries"
                            },
                        selected="COL_AU"
                        )

                        ui.input_select(
                            "colnormalize",
                            "Normalization",
                            {
                                "none": "None",
                                "association": "Association",
                                "jaccard": "Jaccard",
                                "salton": "Salton",
                                "inclusion": "Inclusion",
                                "equivalence": "Equivalence"
                            },
                            selected="association"
                        )

                        with ui.accordion(id="accordion_collaboration_network", multiple=True, open=False):
                            with ui.accordion_panel("Method Parameters"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("collab_network_layout", "Network Layout", {"auto": "Automatic layout", "fr": "Fruchterman-Reingold", "kk": "Kamada-Kawai", "circle": "Circle", "mdrl": "Multi Dimension Scaling", "graphopt": "Graphopt", "sphere": "Sphere", "star": "Star"}, selected="auto")
                                    ui.input_select("collab_clustering_algorithm", "Clustering Algorithm", {"none": "None", "edge_betweenness": "Edge Betweenness", "infomap": "InfoMap", "leading_eigen": "Leading Eigenvalues", "leiden": "Leiden", "louvain": "Louvain", "spinglass": "Spinglass", "walktrap": "Walktrap"}, selected="walktrap")

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric("collabNodes", "Number of Nodes", min=5, max=1000, value=50, step=1)
                                    ui.input_numeric("collab_repulsion", "Repulsion Force", min=0, max=1, value=0.1, step=0.1)

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select("collab_isolates", "Remove Isolated Nodes", {"yes": "Yes", "no": "No"}, selected="yes")
                                    ui.input_numeric("collabedges_min", "Minimum Number of Edges", value=2, step=1, min=0)

                            with ui.accordion_panel("Graphical Parameters"):
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric(
                                        "collab_opacity",
                                        "Opacity",
                                        min=0,
                                        max=1,
                                        value=0.7,
                                        step=0.05
                                    )
                                    ui.input_select(
                                        "collabShortlabel",
                                        "Short Label",
                                        {"Yes": "Yes", "No": "No"},
                                        selected="Yes"
                                    )

                                ui.input_numeric(
                                    "collabLabels",
                                    "Number of labels",
                                    min=0,
                                    max=1000,
                                    value=1000,
                                    step=1
                                )

                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select(
                                        "collablabel_cex",
                                        "Label cex",
                                        {"Yes": "Yes", "No": "No"},
                                        selected="Yes"
                                    )
                                    ui.input_select(
                                        "collab_shape",
                                        "Node Shape",
                                        {
                                            "box": "Box",
                                            "circle": "Circle",
                                            "dot": "Dot",
                                            "ellipse": "Ellipse",
                                            "square": "Square",
                                            "text": "Text"
                                        },
                                        selected="dot"
                                    )
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_numeric(
                                        "collablabelsize",
                                        "Label size",
                                        min=0.0,
                                        max=20,
                                        value=2,
                                        step=0.10
                                    )
                                    ui.input_numeric(
                                        "collabedgesize",
                                        "Edge size",
                                        min=0.5,
                                        max=20,
                                        value=2,
                                        step=0.5
                                    )
                                with ui.layout_column_wrap(width=1 / 2):
                                    ui.input_select(
                                        "collab_shadow",
                                        "Node shadow",
                                        {"Yes": "Yes", "No": "No"},
                                        selected="Yes"
                                    )
                                    ui.input_select(
                                        "collab_curved",
                                        "Edit Nodes",
                                        {"Yes": "Yes", "No": "No"},
                                        selected="No"
                                    )

                    with ui.navset_underline():
                        with ui.nav_panel("Network"):
                            @render.ui
                            def show_collaboration_network():
                                result = collaboration_network_results.get()
                                if result is not None:
                                    plot_collab, _, _, _ = result
                                    return ui.HTML(f'<iframe src="{plot_collab}" width="100%" height="1000px" frameborder="0" style="border:0; outline:none;"></iframe>')
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the collaboration network.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                            
                        with ui.nav_panel("Density"):
                            @render_widget
                            def show_collaboration_density_table():
                                result = collaboration_network_results.get()
                                if result is not None:
                                    _, density_plot, _, _ = result
                                    return density_plot
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the density plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Table"):
                            @render.ui
                            def show_collaboration_table():
                                result = collaboration_network_results.get()
                                if result is not None:
                                    _, _, collab_table, _ = result
                                    return ui.HTML(DT(collab_table, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the collaboration table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

                        with ui.nav_panel("Degree Plot"):
                            @render_widget
                            def show_collaboration_clusters():
                                result = collaboration_network_results.get()
                                if result is not None:
                                    _, _, _, degree_plot = result
                                    return degree_plot
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the degree plot.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

        # --- Countries Collaboration Network Section ---
        with ui.nav_panel("None", value="countries_collaboration_network"):
            with ui.layout_columns(
                col_widths=(8, 4),
                style="margin-bottom: -21px;"
            ):
                with ui.tags.div(style="flex: 1; bottom: 0px;"):
                    ui.h3("📊 Countries Collaboration Network", style="color: #5567BB;")
                    ui.p("The countries collaboration network of the dataset")

                with ui.tags.div(style="flex: 2; display: flex; justify-content: flex-end; gap: 5px; align-items: flex-start; bottom: 0px; width: 100%; flex-wrap: nowrap; min-width: 0;"):
                    ui.input_action_button("run_countries_collaboration_network", "Run Analysis", icon=ICONS["play"])
                    ui.input_action_button("countries_collaboration_network_report", "Add in Report", icon=ICONS["plus"])

                    todaydate = datetime.today()
                    todaydate = todaydate.strftime("%Y-%m-%d")
                    @render.download(
                        label='💾 Download',
                        filename=f"CountriesCollaborationNetwork-{todaydate}.png"
                    )
                    def download_countries_collaboration_network():
                        result = countries_collaboration_network_results.get()
                        if result is not None:
                            plot_countries_map, _ = result
                            yield plotly_download(
                                plot_countries_map,
                                title="Countries Collaboration Network",
                                height=height.get(),
                                dpi=dpi.get()
                            )

                @render.ui
                @reactive.event(input.countries_collaboration_network_report)
                def show_countries_collaboration_network_report():
                    result = countries_collaboration_network_results.get()
                    if result is not None:
                        plot_countries_map, countries_collaboration_tab = result
                        report_excel.set(add_to_report(report_choices, report_excel, [countries_collaboration_tab], [plot_countries_map], "collabworldmap"))
                        selection.set(selection.get() + (f"{list(report_choices.get().keys())[-1]}",))
                        return ui.notification_show("✅ Countries Collaboration Network added to report", duration=5, close_button=False)
                    else:
                        return ui.notification_show("⚠️ Please run the analysis first by clicking the Run Analysis button", duration=5, close_button=False, type="warning")

            with ui.card(full_screen=True):
                with ui.layout_sidebar(fillable=False, fill=False):
                    # Initialize reactive values for results
                    countries_collaboration_network_results = reactive.Value(None)
                    
                    @reactive.effect
                    @reactive.event(input.run_countries_collaboration_network)
                    def run_countries_collaboration_network_analysis():
                        # Show loading modal while calculating (same style as Sources Production over Time)
                        def loading_modal():
                            phrases = [
                                "⏳ Loading... Please wait.",
                                "🌍 Processing countries collaboration network...",
                                "📊 Analyzing international collaborations...",
                                "🌐 Building world map network...",
                                "📈 Computing geographical layouts...",
                                "✨ Almost there! Preparing your world map...",
                                "🎯 Finalizing global visualization...",
                                "🔗 Connecting countries and collaborations...",
                                "🌐 Exploring your scientific landscape...",
                                "🚀 Science mapping in progress...",
                            ]
                            modal = ui.modal(
                                ui.div(
                                    ui.img(
                                        src="https://cisslaboral.laleynext.es/Img/loader-circle.gif",
                                        height="150px",
                                        style="display: block; margin: 0 auto; text-align: center;",
                                    ),
                                    ui.h4(
                                        phrases[0],
                                        id="loading-phrase",
                                        style="font-size: 15px; text-align: center; margin-top: 20px; color: gray;",
                                    ),
                                ),
                                easy_close=False,
                                footer=None,
                            )
                            js = f"""
                            <script>
                            (function() {{
                                var phrases = {phrases};
                                var idx = 0;
                                var el = document.getElementById('loading-phrase');
                                if (el) {{
                                    setInterval(function() {{
                                        idx = (idx + 1) % phrases.length;
                                        el.textContent = phrases[idx];
                                    }}, 1000);
                                }}
                            }})();
                            </script>
                            """
                            return ui.HTML(str(modal) + js)
                        
                        ui.modal_show(loading_modal())
                        try:
                            # Execute analysis (with default parameters for world map collaboration)
                            result = get_world_map_collaboration(
                                df=df,
                                edges_min=1,
                                edgesize=5
                            )
                            
                            # Store results
                            countries_collaboration_network_results.set(result)
                        except Exception as e:
                            ui.notification_show(f"❌ Error in analysis: {str(e)}", type="error", duration=10)
                        finally:
                            ui.modal_remove()

                    with ui.sidebar(id="sidebar_countries_collaboration_network", position="right"):
                        ui.h4("Parameters", style="color: #5567BB;")
                        ui.p("Select the parameters for the countries collaboration network.")
                        ui.markdown("Method Parameters:")
                        ui.input_numeric(
                            "WMedges_min",
                            label="Min edges",
                            value=2,
                            step=1
                        )
                        ui.input_numeric(
                            "WMedgesize",
                            label="Edge size",
                            min=0.1,
                            max=20,
                            value=5
                        )

                    with ui.navset_underline():
                        with ui.nav_panel("World Map"):
                            @render.ui
                            def show_world_map_placeholder():
                                result = countries_collaboration_network_results.get()
                                if result is None:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the world map collaboration.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )
                                else:
                                    return ui.div()  # Empty when there's data
                            
                            @render_widget
                            def show_world_map_collaboration():
                                result = countries_collaboration_network_results.get()
                                if result is not None:
                                    plot_world_map, _ = result
                                    return plot_world_map
                                else:
                                    return None
                        
                        with ui.nav_panel("Table"):
                            @render.ui
                            def show_world_map_collaboration_table():
                                result = countries_collaboration_network_results.get()
                                if result is not None:
                                    _, world_map_table = result
                                    return ui.HTML(DT(world_map_table, style="width=100%;"))
                                else:
                                    return ui.div(
                                        ui.p("Click the Run Analysis button to generate the world map collaboration table.", style="text-align: center; color: #666; font-size: 16px;"),
                                        style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 300px; border: 2px dashed #ddd; border-radius: 10px; margin: 20px;"
                                    )

        # --- Report Section ---
        with ui.nav_panel("None", value="report"):
            ui.h3("⚙️ Report", style="color: #5567BB;")
            ui.p("The report of the analysis")
            
            with ui.card(full_screen=True):
                with ui.layout_column_wrap(width=1 / 2):
                    with ui.card():
                        ui.card_header("Select results to include in the Report", style="background: #4379cd; color: white;")
                        choices = {"empty": ui.span("Empty Report")}
                        ui.input_checkbox_group(
                            "report_selection",
                            "",
                            choices=choices,
                            selected=["empty"],
                        )
                        
                        @reactive.effect
                        def update_selection():
                            user_selection = input.report_selection()
                            selection.set(user_selection)

                        @render.ui
                        @reactive.event(input.go_report)
                        def show_report_selection():
                            choices = report_choices.get() if report_choices.get() != {} else {"empty": ui.span("Empty Report")}
                            return ui.update_checkbox_group(
                                "report_selection",
                                choices=choices,
                                selected=selection.get(),
                            )
                        
                        @render.ui
                        @reactive.event(input.select_all)
                        def select_all_report():
                            selected_choices = choices if report_choices.get() == {} else report_choices.get()
                            selection.set(list(selected_choices.keys()))
                            return ui.update_checkbox_group(
                                "report_selection",
                                selected=selection.get(),
                            )

                        @render.ui
                        @reactive.event(input.deselect_all)
                        def deselect_all_report():
                            selection.set([])
                            return ui.update_checkbox_group(
                                "report_selection",
                                selected=selection.get(),
                            )
                        
                        @render.ui
                        @reactive.event(input.delete)
                        def delete_report():
                            report_choices.set({})
                            report_excel.set(io.BytesIO())
                            selection.set(["empty"])
                            return ui.update_checkbox_group(
                                "report_selection",
                                choices={"empty": ui.span("Empty Report")},
                                selected=selection.get(),
                            )

                    with ui.layout_column_wrap(width=1 / 1):
                        ui.input_action_button("select_all", "Select All", width="50%", icon=ICONS["plus"], class_="btn btn-primary")
                        ui.input_action_button("deselect_all", "Deselect All", width="50%", icon=ICONS["minus"], class_="btn btn-primary")
                        ui.input_action_button("delete", "Delete Report", width="50%", icon=ICONS["delete"], class_="btn btn-danger")

                        with ui.layout_columns(
                            col_widths={"sm": (6, 6)},
                        ):
                            with ui.tags.div(style="flex: 1;"):
                                @render.express()
                                @reactive.event(input.go_report, input.delete)
                                def show_download_report():
                                    todaydate = datetime.today()
                                    todaydate = todaydate.strftime("%Y-%m-%d")
                                    if report_excel.get().getbuffer().nbytes > 0:
                                        @render.download(label="💾 Generate Report", filename=f"BiblioshinyReport-{todaydate}.xlsx")
                                        def download_report():
                                            report = report_excel.get()
                                            yield report.getvalue()
        
        # --- Settings Section ---        
        with ui.nav_panel("None", value="settings"):
            ui.h3("⚙️ Settings", style="color: #5567BB;")
            
            with ui.card(full_screen=True, style="margin-top: 20px;"):
                ui.h4("✨ Biblio AI API Key:")
                ui.markdown("Set a valid API Key to use 'Biblio AI' features powered by Google Gemini. If you don’t have one yet, you can generate it by logging into [AI Studio](https://aistudio.google.com/app/apikey) with your Google account and creating a new API Key.")
                ui.input_password("gemini_api_key", "Enter your Gemini API Key:", placeholder="Enter your Gemini API key here", width="50%")

                @render.ui
                @reactive.event(input.save_api)
                def save_api_key():
                    if len(input.gemini_api_key())>=10:
                        gemini_api_key.set(input.gemini_api_key())
                        masked = "*" * (len(input.gemini_api_key()) - 4) + input.gemini_api_key()[-4:]
                        return ui.markdown(f"✅ API Key has been set: {masked}")
                    else:
                        return ui.markdown("❌ API Key seems to be not valid")

                @render.express()
                @reactive.event(input.reset_api)
                def reset_api_key():
                    _ = gemini_api_key.set("")

                with ui.layout_columns(
                    col_widths={"sm": (12)},
                ):
                    with ui.tags.div(style="flex: 1;"):
                        ui.input_action_button("save_api", "Set API Key", icon=ICONS["save"])
                        ui.input_action_button("reset_api", "Remove API Key", icon=ICONS["delete"])

                ui.hr()
                ui.h4("📊 Plot settings:")
                ui.input_slider("plot_dpi", "Please select the desired DPI", sep="", ticks=True, min=75, max=600, value=300, step=15)
                ui.input_slider("plot_height", "Please select the desired height in inches", sep="", ticks=True, min=5, max=15, value=7, step=1)

                @reactive.calc
                def plot_settings():
                    # Get the values from the inputs
                    dpi.set(input.plot_dpi())
                    height.set(input.plot_height())
                
                @render.express()
                @reactive.event(input.plot_dpi, input.plot_height, input.gemini_api_key)
                def update_plot_settings():
                    plot_settings()


# --- Sidebar Management ---
@render.express()
@reactive.event(input.start_button)
def toggle_sidebar():
    with ui.tags.div(id="sidebar_2", class_="custom-sidebar"):
        with ui.accordion(id="sidebar_accordion_data", multiple=False, open=False):
            # Info Section
            with ui.accordion_panel("Biblioshiny", icon=ICONS["home_colored"]):
                ui.input_action_button("go_about_2", "Biblioshiny", class_="sidebar-button", icon=ICONS["home"])
            # Data Section
            with ui.accordion_panel("Data", icon=ICONS["database_colored"]):
                ui.input_action_button("go_import_2", "Import or Load", class_="sidebar-button", icon=ICONS["data"])
                ui.input_action_button("go_api_2", "API", class_="sidebar-button", icon=ICONS["api"])
                ui.input_action_button("go_collections_2", "Merge Collection", class_="sidebar-button", icon=ICONS["merge"])

            # Filters Section
            with ui.accordion_panel("Filters", icon=ICONS["filters_colored"]):
                ui.input_action_button("go_filters", "Filters", class_="sidebar-button", icon=ICONS["filters"])

            # Analysis Section
            with ui.accordion_panel("Overview", icon=ICONS["play_colored"]):
                ui.input_action_button("go_main", "Main Information", class_="sidebar-button", icon=ICONS["overview"])
                ui.input_action_button("go_annual_scientific_production", "Annual Scientific Production", class_="sidebar-button", icon=ICONS["annual_growth_rate"])
                ui.input_action_button("go_average_citations_per_year", "Average Citations per Year", class_="sidebar-button", icon=ICONS["average_citations_per_doc"])
                ui.input_action_button("go_three_field_plot", "Three-Field Plot", class_="sidebar-button", icon=ICONS["overview"])
            with ui.accordion_panel("Sources", icon=ICONS["sources_colored"]):
                ui.input_action_button("go_most_relevant_sources", "Most Relevant Sources", class_="sidebar-button", icon=ICONS["book_open"] if "book_open" in ICONS else ICONS["sources"]),
                ui.input_action_button("go_most_local_cited_sources", "Most Local Cited Sources", class_="sidebar-button", icon=ICONS["book"] if "book" in ICONS else ICONS["sources"]),
                ui.input_action_button("go_bradfords_law", "Bradford's Law", class_="sidebar-button", icon=ICONS["annual_growth_rate"]),
                ui.input_action_button("go_sources_local_impact", "Sources' Local Impact", class_="sidebar-button", icon=ICONS["star"] if "star" in ICONS else ICONS["sources"]),
                ui.input_action_button("go_sources_production_over_time", "Sources' Production over Time", class_="sidebar-button", icon=ICONS["calendar"] if "calendar" in ICONS else ICONS["timespan"]),
            with ui.accordion_panel("Authors", icon=ICONS["authors_colored"]):
                # Authors Section
                ui.span("Authors", style="color: gray;")
                ui.input_action_button("go_most_relevant_authors", "Most Relevant Authors", class_="sidebar-button", icon=ICONS["authors"])
                ui.input_action_button("go_most_local_cited_authors", "Most Local Cited Authors", class_="sidebar-button", icon=ICONS["authors_single_authored_docs"])
                ui.input_action_button("go_authors_production_over_time", "Authors' Production over Time", class_="sidebar-button", icon=ICONS["annual_growth_rate"])
                ui.input_action_button("go_lotkas_law", "Lotka's Law", class_="sidebar-button", icon=ICONS["overview"])
                ui.input_action_button("go_authors_local_impact", "Authors' Local Impact", class_="sidebar-button", icon=ICONS["star"] if "star" in ICONS else ICONS["authors"])
                # Affiliations Section
                ui.span("Affiliations", style="color: gray;")
                ui.input_action_button("go_most_relevant_affiliations", "Most Relevant Affiliations", class_="sidebar-button", icon=ICONS["database"])
                ui.input_action_button("go_affiliations_production_over_time", "Affiliations' Production over Time", class_="sidebar-button", icon=ICONS["annual_growth_rate"])
                # Countries Section
                ui.span("Countries", style="color: gray;")
                ui.input_action_button("go_corresponding_authors_countries", "Corresponding Author's Countries", class_="sidebar-button", icon=ICONS["international_co_authorship"])
                ui.input_action_button("go_countries_scientific_production", "Countries' Scientific Production", class_="sidebar-button", icon=ICONS["international_co_authorship"])
                ui.input_action_button("go_countries_production_over_time", "Countries' Production over Time", class_="sidebar-button", icon=ICONS["annual_growth_rate"])
                ui.input_action_button("go_most_cited_countries", "Most Cited Countries", class_="sidebar-button", icon=ICONS["book"])
            with ui.accordion_panel("Documents", icon=ICONS["documents_colored"]):
                # Documents Section
                ui.span("Documents", style="color: gray;")
                ui.input_action_button("go_most_global_cited_documents", "Most Global Cited Documents", class_="sidebar-button", icon=ICONS["documents"])
                ui.input_action_button("go_most_local_cited_documents", "Most Local Cited Documents", class_="sidebar-button", icon=ICONS["documents"])

                # Cited References Section
                ui.span("Cited References", style="color: gray;")
                ui.input_action_button("go_most_local_cited_references", "Most Local Cited References", class_="sidebar-button", icon=ICONS["references"])
                ui.input_action_button("go_references_spectroscopy", "References Spectroscopy", class_="sidebar-button", icon=ICONS["references"])

                # Words Section
                ui.span("Words", style="color: gray;")
                ui.input_action_button("go_most_frequent_words", "Most Frequent Words", class_="sidebar-button", icon=ICONS["authors_keywords_de"])
                ui.input_action_button("go_wordcloud", "WordCloud", class_="sidebar-button", icon=ICONS["authors_keywords_de"])
                ui.input_action_button("go_treemap", "TreeMap", class_="sidebar-button", icon=ICONS["overview"])
                ui.input_action_button("go_words_frequency_over_time", "Words' Frequency over Time", class_="sidebar-button", icon=ICONS["annual_growth_rate"])
                ui.input_action_button("go_trend_topics", "Trend Topics", class_="sidebar-button", icon=ICONS["annual_growth_rate"])

            with ui.accordion_panel("Clustering", icon=ICONS["clustering_colored"]):
                ui.input_action_button("go_clustering", "Clustering", class_="sidebar-button", icon=ICONS["clustering"])
            
            with ui.accordion_panel("Conceptual Structure", icon=ICONS["conceptual_structure_colored"]):
                ui.span("Network Approach", style="color: gray;")
                ui.input_action_button("go_cooccurrence_network", "Co-occurrence Network", class_="sidebar-button", icon=ICONS["clustering"])
                ui.input_action_button("go_thematic_map", "Thematic Map", class_="sidebar-button", icon=ICONS["overview"])
                ui.input_action_button("go_thematic_evolution", "Thematic Evolution", class_="sidebar-button", icon=ICONS["annual_growth_rate"])

                ui.span("Factorial Approach", style="color: gray;")
                ui.input_action_button("go_factorial_analysis", "Factorial Analysis", class_="sidebar-button", icon=ICONS["overview"])

            with ui.accordion_panel("Intellectual Structure", icon=ICONS["intellectual_structure_colored"]):
                ui.input_action_button("go_citation_network", "Citation Network", class_="sidebar-button", icon=ICONS["references"])
                ui.input_action_button("historiograph", "Historiograph", class_="sidebar-button", icon=ICONS["annual_growth_rate"])

            with ui.accordion_panel("Social Structure", icon=ICONS["social_structure_colored"]):
                ui.input_action_button("go_collaboration_network", "Collaboration Network", class_="sidebar-button", icon=ICONS["co_authors_per_doc"])
                ui.input_action_button("go_countries_collaboration_network", "Countries Collaboration Network", class_="sidebar-button", icon=ICONS["international_co_authorship"])

            with ui.accordion_panel("Report", icon=ICONS["report_colored"]):
                ui.input_action_button("go_report", "Report", class_="sidebar-button", icon=ICONS["report"])
            with ui.accordion_panel("Settings", icon=ICONS["settings_colored"]):
                ui.input_action_button("go_settings", "Settings", class_="sidebar-button", icon=ICONS["settings"])

        # --- Footer ---
        # Use static positioning and margin-top to avoid overlap with accordion content
        with ui.tags.footer(
            class_="custom-footer",
            style=(
            "background: #5567BB; color: white; text-align: center; padding: 10px 0;"
            "position: static; width: 300px; z-index: 1000; margin-top: 30px;"
            "transition: background-color 0.3s ease;"
            ),
        ):
            ui.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: center;">
            <span style="margin-right: 8px;">© 2025</span>
            <a href="https://www.bibliometrix.org/home/" style="display: flex; align-items: center;">
                <img src="https://www.bibliometrix.org/logo_new.png" height="20px" style="filter: invert(100%) brightness(10000%); display: inline-block; vertical-align: middle;">
            </a>
            <a href="https://www.bibliometrix.org/" style="color: #fff; text-decoration: underline; display: inline-block; vertical-align: middle; margin-left: 10px;" target="_blank">
                Bibliometrix
            </a>
            </div>
            <p style="font-size: 9px">Version: 1.0.0 - Shiny for Python Based Application</p>
            """
            )


# --- Javascript for Sidebar ---
ui.tags.script("""
    // Helper to show/hide both sidebars in a coordinated way
    function setSidebarState(show) {
        const sidebar = document.getElementById("sidebar");
        const sidebar_2 = document.getElementById("sidebar_2");
        const content = document.getElementById("mainContent");
        if (sidebar) sidebar.classList.toggle("sidebar-hidden", !show);
        if (sidebar_2) sidebar_2.classList.toggle("sidebar-hidden", !show);
        if (content) content.classList.toggle("full-width", !show);
    }

    // Hide sidebars on page load
    document.addEventListener("DOMContentLoaded", function() {
        setSidebarState(false);
    });

    // Toggle both sidebars on button click
    document.getElementById("toggleSidebar").addEventListener("click", function() {
        const sidebar = document.getElementById("sidebar");
        // If either sidebar is visible, hide both; otherwise, show both
        const isVisible = sidebar && !sidebar.classList.contains("sidebar-hidden");
        setSidebarState(!isVisible);
    });

    // Listen for Shiny events that might add/remove sidebar_2 dynamically
    // and keep them in sync
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0) {
                // Always keep both sidebars in the same state
                const sidebar = document.getElementById("sidebar");
                const sidebar_2 = document.getElementById("sidebar_2");
                if (sidebar && sidebar_2) {
                    const sidebarHidden = sidebar.classList.contains("sidebar-hidden");
                    sidebar_2.classList.toggle("sidebar-hidden", sidebarHidden);
                }
            }
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Show both sidebars when 'start_button' is clicked
    document.addEventListener("click", function(e) {
        if (e.target && e.target.id === "start_button") {
            setSidebarState(true);
        }
    });
""")


# --- Navigation Logic ---
# This section handles the navigation logic between the main panels of the app.
# Each handler listens for an event (typically a click on a sidebar button)
# and updates the selected main panel via ui.update_navs("hidden_tabs", selected=...)

# --- Section 1: Info ---
@reactive.effect
@reactive.event(input.btn_import_data)
def _():
    ui.update_navs("hidden_tabs", selected="import")

@reactive.effect
@reactive.event(input.go_about)
def _():
    ui.update_navs("hidden_tabs", selected="info")

@reactive.effect
@reactive.event(input.go_about_2)
def _():
    ui.update_navs("hidden_tabs", selected="info")

# --- Section 2: Data ---
@reactive.effect
@reactive.event(input.go_import)
def _():
    ui.update_navs("hidden_tabs", selected="import")

@reactive.effect
@reactive.event(input.go_import_2)  
def _():
    ui.update_navs("hidden_tabs", selected="import")

@reactive.effect
@reactive.event(input.go_api)
def _():
    ui.update_navs("hidden_tabs", selected="API")

@reactive.effect
@reactive.event(input.go_api_2)
def _():
    ui.update_navs("hidden_tabs", selected="API")

@reactive.effect
@reactive.event(input.go_collections)
def _():
    ui.update_navs("hidden_tabs", selected="collections")

@reactive.effect
@reactive.event(input.go_collections_2)
def _():
    ui.update_navs("hidden_tabs", selected="collections")

# --- Section 3: Filters ---
@reactive.effect
@reactive.event(input.go_filters)
def _():
    ui.update_navs("hidden_tabs", selected="filters")

# --- Section 4: Analysis (Overview) ---
@reactive.effect
@reactive.event(input.go_main)
def _():
    ui.update_navs("hidden_tabs", selected="overview")

@reactive.effect
@reactive.event(input.go_annual_scientific_production)
def _():
    ui.update_navs("hidden_tabs", selected="annual_scientific_production")

@reactive.effect
@reactive.event(input.go_average_citations_per_year)
def _():
    ui.update_navs("hidden_tabs", selected="average_citations_per_year")

@reactive.effect
@reactive.event(input.go_three_field_plot)
def _():
    ui.update_navs("hidden_tabs", selected="three_field_plot")

# --- Section 5: Sources ---
@reactive.effect
@reactive.event(input.go_most_relevant_sources)
def _():
    ui.update_navs("hidden_tabs", selected="most_relevant_sources")

@reactive.effect
@reactive.event(input.go_most_local_cited_sources)
def _():
    ui.update_navs("hidden_tabs", selected="most_local_cited_sources")

@reactive.effect
@reactive.event(input.go_bradfords_law)
def _():
    ui.update_navs("hidden_tabs", selected="bradfords_law")

@reactive.effect
@reactive.event(input.go_sources_local_impact)
def _():
    ui.update_navs("hidden_tabs", selected="sources_local_impact")

@reactive.effect
@reactive.event(input.go_sources_production_over_time)
def _():
    ui.update_navs("hidden_tabs", selected="sources_production")

# --- Section 6: Authors ---
@reactive.effect
@reactive.event(input.go_most_relevant_authors)
def _():
    ui.update_navs("hidden_tabs", selected="most_relevant_authors")

@reactive.effect
@reactive.event(input.go_most_local_cited_authors)
def _():
    ui.update_navs("hidden_tabs", selected="most_local_cited_authors")

@reactive.effect
@reactive.event(input.go_authors_production_over_time)
def _():
    ui.update_navs("hidden_tabs", selected="authors_production")

@reactive.effect
@reactive.event(input.go_lotkas_law)
def _():
    ui.update_navs("hidden_tabs", selected="lotka_law")

@reactive.effect
@reactive.event(input.go_authors_local_impact)
def _():
    ui.update_navs("hidden_tabs", selected="authors_local_impact")

@reactive.effect
@reactive.event(input.go_most_relevant_affiliations)
def _():
    ui.update_navs("hidden_tabs", selected="most_relevant_affiliations")

@reactive.effect
@reactive.event(input.go_affiliations_production_over_time)
def _():
    ui.update_navs("hidden_tabs", selected="affiliations_production")

@reactive.effect
@reactive.event(input.go_corresponding_authors_countries)
def _():
    ui.update_navs("hidden_tabs", selected="corresponding_authors")

@reactive.effect
@reactive.event(input.go_countries_scientific_production)
def _():
    ui.update_navs("hidden_tabs", selected="countries_scientific_production")

@reactive.effect
@reactive.event(input.go_countries_production_over_time)
def _():
    ui.update_navs("hidden_tabs", selected="countries_production_over_time")

@reactive.effect
@reactive.event(input.go_most_cited_countries)
def _():
    ui.update_navs("hidden_tabs", selected="most_cited_countries")

# --- Section 7: Documents ---
@reactive.effect
@reactive.event(input.go_most_global_cited_documents)
def _():
    ui.update_navs("hidden_tabs", selected="most_global_cited_documents")

@reactive.effect
@reactive.event(input.go_most_local_cited_documents)
def _():
    ui.update_navs("hidden_tabs", selected="most_local_cited_documents")

@reactive.effect
@reactive.event(input.go_most_local_cited_references)
def _():
    ui.update_navs("hidden_tabs", selected="most_local_cited_references")

@reactive.effect
@reactive.event(input.go_references_spectroscopy)
def _():
    ui.update_navs("hidden_tabs", selected="references_spectroscopy")

@reactive.effect
@reactive.event(input.go_most_frequent_words)
def _():
    ui.update_navs("hidden_tabs", selected="most_frequent_words")

@reactive.effect
@reactive.event(input.go_wordcloud)
def _():
    ui.update_navs("hidden_tabs", selected="wordcloud")

@reactive.effect
@reactive.event(input.go_treemap)
def _():
    ui.update_navs("hidden_tabs", selected="treemap")

@reactive.effect
@reactive.event(input.go_words_frequency_over_time)
def _():
    ui.update_navs("hidden_tabs", selected="words_frequency_over_time")

@reactive.effect
@reactive.event(input.go_trend_topics)
def _():
    ui.update_navs("hidden_tabs", selected="trend_topics")

# --- Section 8: Network Analysis ---
@reactive.effect
@reactive.event(input.go_cooccurrence_network)
def _():
    ui.update_navs("hidden_tabs", selected="co_occurrence_network")

@reactive.effect
@reactive.event(input.go_citation_network)
def _():
    ui.update_navs("hidden_tabs", selected="co_citation_network")

# --- Section 9: Cluster Analysis ---
@reactive.effect
@reactive.event(input.go_clustering)
def _():
    ui.update_navs("hidden_tabs", selected="cluster_analysis")

# --- Section 10: Co-occurrence Network (alias) ---
@reactive.effect
@reactive.event(input.go_cooccurrence_network)
def _():
    ui.update_navs("hidden_tabs", selected="co-occurrence-network")

@reactive.effect
@reactive.event(input.go_thematic_map)
def _():
    ui.update_navs("hidden_tabs", selected="thematic_map")

# --- Section 11: Thematic Evolution ---
@reactive.effect
@reactive.event(input.go_thematic_evolution)
def _():
    ui.update_navs("hidden_tabs", selected="thematic_evolution")

# --- Section 12: Factorial Approach ---
@reactive.effect
@reactive.event(input.go_factorial_analysis)
def _():
    ui.update_navs("hidden_tabs", selected="factorial_analysis")

# --- Section 13: Co-citation Network (alias) ---
@reactive.effect
@reactive.event(input.go_citation_network)
def _():
    ui.update_navs("hidden_tabs", selected="co-citation-network")

@reactive.effect
@reactive.event(input.historiograph)
def _():
    ui.update_navs("hidden_tabs", selected="historiograph")

# --- Section 14: Collaboration Network ---
@reactive.effect
@reactive.event(input.go_collaboration_network)
def _():
    ui.update_navs("hidden_tabs", selected="collaboration_network")

@reactive.effect
@reactive.event(input.go_countries_collaboration_network)
def _():
    ui.update_navs("hidden_tabs", selected="countries_collaboration_network")

# --- Section 15: Report ---
@reactive.effect
@reactive.event(input.go_report)
def _():
    ui.update_navs("hidden_tabs", selected="report")

# --- Section 16: Settings ---
@reactive.effect
@reactive.event(input.go_settings)
def _():
    ui.update_navs("hidden_tabs", selected="settings")

@reactive.effect
@reactive.event(input.go_settings_2)
def _():
    ui.update_navs("hidden_tabs", selected="settings")
