document.addEventListener("DOMContentLoaded", () => {
    const recordBtn = document.getElementById('recordBtn');
    const retryBtn = document.getElementById('retryBtn');
    const nextBtn = document.getElementById('nextBtn');
    const resultDiv = document.getElementById('result');
    const questionText = document.getElementById('questionText');
    const generateDocxBtn = document.getElementById('generateDocxBtn');

    let currentIndex = 0;
    let mediaRecorder, audioChunks = [], structuredData = {}, question_key = '';

    // 👉 Load câu hỏi tiếp theo
    function fetchNextQuestion() {
        fetch(`/next_question?index=${currentIndex}`)
            .then(response => response.json())
            .then(data => {
                if (data.question) {
                    questionText.textContent = data.question;
                    question_key = data.key;
                } else {
                    questionText.textContent = "✅ All questions completed.";
                    nextBtn.style.display = 'none';
                    recordBtn.style.display = 'none';
                }
            });
    }

    // 🎙️ Bắt đầu & dừng ghi âm
    recordBtn.addEventListener('click', async () => {
        if (recordBtn.textContent === 'Start Recording') {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => audioChunks.push(event.data);

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const formData = new FormData();
                formData.append('audio', audioBlob, 'recording.wav');
                formData.append('question_key', question_key);

                resultDiv.innerHTML = '⏳ Processing transcript...';

                try {
                    const response = await fetch('/transcribe', { method: 'POST', body: formData });
                    const data = await response.json();
                    structuredData[question_key] = data.structured_data[question_key];
                    resultDiv.innerHTML = `<strong>📝 Transcript:</strong><br>${data.text}`;
                    retryBtn.style.display = 'inline-block';
                    nextBtn.style.display = 'inline-block';
                } catch {
                    resultDiv.innerHTML = '❌ Error processing audio.';
                }
            };

            mediaRecorder.start();
            recordBtn.textContent = 'Stop Recording';
        } else {
            mediaRecorder.stop();
            recordBtn.textContent = 'Start Recording';
        }
    });

    // 🔄 Ghi lại câu hỏi
    retryBtn.addEventListener('click', () => {
        resultDiv.innerHTML = '📝 Ready to record again...';
        retryBtn.style.display = 'none';
        nextBtn.style.display = 'none';
    });

    // ⏭️ Chuyển sang câu tiếp theo
    nextBtn.addEventListener('click', () => {
        currentIndex++;
        fetchNextQuestion();
        resultDiv.innerHTML = '🎤 Ready to record...';
        retryBtn.style.display = 'none';
        nextBtn.style.display = 'none';
    });

    // 📄 Tạo file DOCX
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
                resultDiv.innerHTML = `<a href="${data.html_file}" target="_blank" class="btn download-link">⬇️ Download your DOCX CV</a>`;
            }
        } catch (err) {
            console.error('Error:', err);
            resultDiv.innerHTML = '❌ Error generating DOCX.';
        }
    });

    fetchNextQuestion(); // Load câu hỏi đầu tiên khi trang được tải
});
