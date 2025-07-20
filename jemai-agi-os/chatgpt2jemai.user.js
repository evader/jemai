// ==UserScript==
// @name         JEMAI Chat Sync for ChatGPT
// @match        https://chat.openai.com/*
// ==/UserScript==
(function() {
    setInterval(()=>{
        const answers = document.querySelectorAll('div[data-message-author-role="assistant"]');
        if(answers.length > 0){
            const target = answers[answers.length-1].innerText;
            fetch('http://localhost:8181/new_reply', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: target, time: new Date().toISOString() })
            });
        }
    }, 3000);
})();
