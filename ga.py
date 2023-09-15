from bs4 import BeautifulSoup
import shutil
import pathlib
import logging
import streamlit as st


def add_analytics_tag():
    # replace G-XXXXXXXXXX to your web app's ID
    
    analytics_js = """
    <!-- Global site tag (gtag.js) - Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-JNFEY2N9PE"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-JNFEY2N9PE');
    </script>
    <div id="G-JNFEY2N9PE"></div>
    """
    analytics_id = "G-JNFEY2N9PE"

    
    # Identify html path of streamlit
    index_path = pathlib.Path(st.__file__).parent / "static" / "index.html"
    logging.info(f'editing {index_path}')
    soup = BeautifulSoup(index_path.read_text(), features="html.parser")
    if not soup.find(id=analytics_id): # if id not found within html file
        bck_index = index_path.with_suffix('.bck')
        if bck_index.exists():
            shutil.copy(bck_index, index_path)  # backup recovery
        else:
            shutil.copy(index_path, bck_index)  # save backup
        html = str(soup)
        new_html = html.replace('<head>', '<head>\n' + analytics_js) 
        index_path.write_text(new_html) # insert analytics tag at top of head
