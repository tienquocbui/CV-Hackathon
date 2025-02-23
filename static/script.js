document.addEventListener("DOMContentLoaded", () => {
    const recordBtn = document.getElementById('recordBtn');
    const questionText = document.getElementById('questionText');
    const summaryContent = document.getElementById('summaryContent');
    const generateDocxBtn = document.getElementById('generateDocxBtn');
    const fileOptionsDiv = document.getElementById('fileOptions');
    const resultDiv = document.getElementById('result');
    
    let currentIndex = 0;
    let mediaRecorder, audioChunks = [];
    let structuredData = {};
    // Function to read text aloud
    function readAloud(text) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';  // You can change the language if needed (e.g., 'en-GB' for British English)
        window.speechSynthesis.speak(utterance);
    }
    // 🎯 Fetch the next question
    function fetchNextQuestion() {
        fetch(`/next_question?index=${currentIndex}`)
            .then(response => response.json())
            .then(data => {
                if (data.question) {
                    questionText.textContent = `${currentIndex + 1}. ${data.question}`;
                    recordBtn.style.display = 'inline-flex';
                    readAloud(data.question);

                } else {
                    questionText.innerHTML = `<img src="/static/assets/check.svg" alt="Check" style="width:20px; vertical-align:middle; margin-right:8px;">All questions completed.`;
                    recordBtn.style.display = 'none';
                }
            });
    }

    function addToSummary(question, transcript) {
        const item = document.createElement('div');
        item.classList.add('summary-item');
        item.innerHTML = `
        <p class="summary-question">${question}</p>
        <p class="summary-answer">${transcript}</p>
      `;

        summaryContent.appendChild(item);
        structuredData[question] = transcript;
    }

    // 🎙️ Handle Recording
    recordBtn.addEventListener('click', async () => {
        if (recordBtn.classList.contains('recording')) {

            mediaRecorder.stop();
            recordBtn.classList.remove('recording');
            recordBtn.innerHTML = `<img src="/static/assets/play_circle.svg" class="record-icon" /> Start Recording`;
        } else {

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => audioChunks.push(event.data);

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const formData = new FormData();
                formData.append('audio', audioBlob);
                formData.append('language', 'en');
                formData.append('question_key', questionText.textContent);

                try {
                    const response = await fetch('/transcribe', { method: 'POST', body: formData });
                    const data = await response.json();

                    if (data.text) {
                        addToSummary(questionText.textContent, data.text);
                        currentIndex++;
                        fetchNextQuestion();
                    } else {
                        alert('Error: Could not transcribe.');
                    }
                } catch (err) {
                    console.error('Transcription error:', err);
                }
            };

            mediaRecorder.start();
            recordBtn.classList.add('recording');
            recordBtn.innerHTML = `<img src="/static/assets/stop_circle.svg" class="record-icon" /> Stop Recording`;
        }
    });
    generateDocxBtn.addEventListener('click', async () => {
        resultDiv.innerHTML = '🔄 Generating DOCX...';
        try {
            const response = await fetch('/generate_docx', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ structured_data: structuredData })
            });
            const data = await response.json();
            if (data.file) {
                // Show download link for DOCX file
                downloadDocxBtn.href = data.file;
                downloadDocxBtn.style.display = 'inline-block';

                // Optionally, show the HTML view link if HTML is generated
                if (data.html_file) {
                    viewHtmlBtn.href = data.html_file;
                    viewHtmlBtn.style.display = 'inline-block';
                }

                // Show both options
                fileOptionsDiv.style.display = 'block';
            }
        } catch (err) {
            console.error('Error:', err);
            resultDiv.innerHTML = '❌ Error generating DOCX.';
        }
    });
    fetchNextQuestion();
});
