# css.py
CSS_STYLES = """
<style>
    :root {
        --background: #151e17;
        --my-message: #00e571;
        --their-message: #29332a;
        --text-dark: #FFFFFF;
        --text-light: #FFFFFF;
        --animation-duration: 0.3s;
    }
    * { 
        box-sizing: border-box; 
        margin: 0; 
        padding: 0; 
    }
    body { 
        font-family: 'Roboto', sans-serif; 
        background: var(--background); 
        padding: 20px; 
        color: var(--text-light); 
    }
    .container { 
        max-width: 800px; 
        margin: 0 auto; 
    }
    .message { 
        display: flex; 
        margin-bottom: 15px; 
        opacity: 0; 
        transform: translateY(20px); 
        animation: fadeInUp var(--animation-duration) ease-out forwards; 
    }
    @keyframes fadeInUp {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .message.my { 
        justify-content: flex-end; 
        animation-delay: calc(var(--animation-duration) * 0.5);
    }
    .message.their { 
        justify-content: flex-start; 
        animation-delay: calc(var(--animation-duration) * 0.25);
    }
    .bubble { 
        max-width: 70%; 
        padding: 12px 16px; 
        border-radius: 20px; 
        position: relative; 
        word-wrap: break-word; 
        overflow-wrap: break-word; 
        transition: transform 0.2s ease, box-shadow 0.2s ease; 
    }
    .bubble:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
    }
    .my .bubble { 
        background: var(--my-message); 
        color: var(--text-light); 
        border-bottom-right-radius: 4px; 
    }
    .their .bubble { 
        background: var(--their-message); 
        color: var(--text-dark); 
        border-bottom-left-radius: 4px; 
    }
    .meta { 
        display: flex; 
        justify-content: space-between; 
        font-size: 0.8em; 
        margin-bottom: 5px; 
    }
    .sender { 
        font-weight: bold; 
        margin-right: 10px; 
    }
    .date { 
        opacity: 0.8; 
    }
    .media { 
        margin-top: 10px; 
        border-radius: 12px; 
        overflow: hidden; 
        transition: transform 0.2s ease; 
    }
    .media:hover {
        transform: scale(1.02);
    }
    video { 
        width: 100%; 
        max-width: 400px; 
        border-radius: 12px; 
    }
    audio { 
        width: 100%; 
        min-width: 250px; 
    }
    img { 
        max-width: 100%; 
        height: auto; 
        border-radius: 12px; 
    }
    .file-card { 
        padding: 10px; 
        background: rgba(255, 255, 255, 0.1); 
        border-radius: 8px; 
        margin-top: 8px; 
        transition: transform 0.2s ease; 
    }
    .file-card:hover {
        transform: scale(1.02);
    }
    .forward { 
        font-size: 0.8em; 
        color: rgba(255, 255, 255, 0.7); 
        margin-bottom: 5px; 
    }
    @media (max-width: 600px) { 
        .bubble { 
            max-width: 85%; 
        } 
    }
</style>
"""