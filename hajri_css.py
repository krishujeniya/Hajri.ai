# hajri_css.py
CSS="""
<style>
    /* --- 1. Root & Body --- */
    :root {
        --logo-blue: #007bff;
        --logo-blue-dark: #0056b3;
        --danger-color: #ef4444;
        --danger-color-hover: #dc2626;
        
        --text-color: #FFFFFF;
        --text-color-light: #A0A0A0;
        --bg-color: #000000;
        
        /* The "Crystal Glass" Effect */
        --glass-bg: rgba(40, 40, 40, 0.7);
        --glass-border: 1px solid rgba(255, 255, 255, 0.15);
        --glass-blur: backdrop-filter: blur(14px);
        --glass-radius: 16px;
        --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    body, .stApp {
        color: var(--text-color);
        background-color: var(--bg-color);
    }

    /* --- 2. Typography --- */
    h1, h2, h3, .stMarkdown { color: var(--text-color); }
    h1 { font-weight: 800; }
    h2 { font-weight: 700; }
    h3 { font-weight: 600; }
    .stCaption { color: var(--text-color-light); }

    /* --- 3. Main App Header (Styles for the st.columns layout) --- */
    .centered-user-info {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 70px; /* Vertically aligns with the 70px logo */
        text-align: center;
    }
    .centered-user-info strong {
        color: var(--text-color);
        font-size: 1.2rem;
        font-weight: 600;
    }
    .centered-user-info span {
        font-size: 0.9rem;
        color: var(--text-color-light);
    }
    
    /* Target the logout button specifically in the 3rd column */
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stButton"] button {
        background-color: var(--glass-bg);
        border: var(--glass-border);
        color: var(--text-color-light);
        -webkit-backdrop-filter: var(--glass-blur);
        backdrop-filter: var(--glass-blur);
        box-shadow: var(--glass-shadow);
        border-radius: 12px;
        font-weight: 500;
        width: 100%; /* Make it fill the column */
        transition: all 0.2s ease;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stButton"] button:hover {
        background-color: rgba(60, 60, 60, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: var(--text-color);
    }
    
    /* --- 4. Login Screen specific styles --- */
    .login-container {
        text-align: center;
        margin-top: 3rem;
        margin-bottom: 2rem;
    }
    .login-logo {
        width: 120px;
        margin-bottom: 20px;
        border-radius: 50%;
        box-shadow: 0 0 30px rgba(0, 123, 255, 0.6);
    }
    .login-container h1 { color: var(--text-color); }
    .login-container h3 { color: var(--text-color-light); }

    /* --- 5. Main "Glass" Containers (st.container(border=True)) --- */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--glass-bg);
        border-radius: var(--glass-radius);
        border: var(--glass-border);
        padding: 2.5rem;
        -webkit-backdrop-filter: var(--glass-blur);
        backdrop-filter: var(--glass-blur);
        box-shadow: var(--glass-shadow);
        margin-bottom: 1.5rem;
    }
    
    /* --- 6. Tabs (Glass Style Fix) --- */
    button[data-baseweb="tab"] {
        height: 55px;
        background-color: var(--glass-bg);
        border: var(--glass-border);
        border-radius: 14px;
        color: var(--text-color-light);
        transition: all 0.2s ease;
        padding: 0 30px;
        font-size: 1.1em;
        font-weight: 500;
        -webkit-backdrop-filter: var(--glass-blur);
        backdrop-filter: var(--glass-blur);
        box-shadow: var(--glass-shadow);
    }
    button[data-baseweb="tab"]:hover {
        background-color: rgba(60, 60, 60, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: var(--text-color);
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--logo-blue);
        border: none;
        color: var(--text-color);
        font-weight: 600;
        box-shadow: 0 8px 20px 0 rgba(0, 123, 255, 0.4);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        margin-bottom: 2.5rem;
    }
    
    /* --- 7. Widgets (Inputs, Selects) --- */
    .stTextInput>div>div>input, 
    .stSelectbox>div>div, 
    .stFileUploader>div>div>button,
    .stTextArea>div>div {
        background-color: rgba(60, 60, 60, 0.7);
        color: var(--text-color);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* --- 8. Buttons --- */
    [data-testid="stButton"]>button {
        font-weight: 600;
        border-radius: 12px;
        padding: 0.8rem 2rem;
        border: none;
        box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        transition: all 0.2s ease-in-out;
        background-color: var(--logo-blue);
        color: white;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stButton"]>button:hover {
        background-color: var(--logo-blue-dark);
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(0, 123, 255, 0.4);
    }
    /* Danger Button */
    [data-testid="stButton"] button[kind="primary"] { 
         background-color: var(--danger-color);
    }
     [data-testid="stButton"] button[kind="primary"]:hover {
         background-color: var(--danger-color-hover);
    }
    
    /* --- 9. Metric Display --- */
    [data-testid="stMetric"] {
        background-color: var(--glass-bg);
        border: var(--glass-border);
        border-radius: var(--glass-radius);
        padding: 2rem;
        text-align: center;
        -webkit-backdrop-filter: var(--glass-blur);
        backdrop-filter: var(--glass-blur);
    }
    
    /* --- 10. Alerts and Infos (Glass Style) --- */
    [data-testid="stAlert"] {
        background-color: var(--glass-bg);
        border: var(--glass-border);
        border-radius: var(--glass-radius);
        -webkit-backdrop-filter: var(--glass-blur);
        backdrop-filter: var(--glass-blur);
        padding: 1.5rem;
        border-left-width: 5px;
        border-left-style: solid;
    }
    [data-testid="stAlert"] .st-emotion-cache-1wivap2 { color: var(--text-color); }
    [data-testid="stAlert"][data-baseweb="notification"][kind="info"] { border-left-color: var(--logo-blue); }
    [data-testid="stAlert"][data-baseweb="notification"][kind="warning"] { border-left-color: #fbbf24; }
    [data-testid="stAlert"][data-baseweb="notification"][kind="error"] { border-left-color: var(--danger-color); }
    [data-testid="stAlert"][data-baseweb="notification"][kind="success"] { border-left-color: #059669; }

    /* --- 11. Hide Sidebar --- */
    [data-testid="stSidebar"] {
        display: none;
    }
</style>
"""
