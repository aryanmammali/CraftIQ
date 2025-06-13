// Chatbot Section
document.getElementById("sendBtn").addEventListener("click", function () {
    const chatInput = document.getElementById("chatInput").value.trim();
    const chatBox = document.getElementById("chatBox");

    if (chatInput === "") return;

    chatBox.innerHTML += `<p><strong>You:</strong> ${chatInput}</p>`;

    fetch("/chatbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: chatInput }),
    })
    .then(response => response.json())
    .then(data => {
        const botResponse = data.response || "Something went wrong.";
        chatBox.innerHTML += `<p><strong>Bot:</strong> ${botResponse}</p>`;
        chatBox.scrollTop = chatBox.scrollHeight;
    })
    .catch(error => {
        console.error(error);
        chatBox.innerHTML += `<p><strong>Bot:</strong> Error communicating with the server.</p>`;
    });

    document.getElementById("chatInput").value = "";
});

// Image Upload Section
document.getElementById("analyzeImageBtn").addEventListener("click", function () {
    const fileInput = document.getElementById("fileInput").files[0];
    const formData = new FormData();
    const imageResult = document.getElementById("imageResult");

    if (!fileInput) {
        imageResult.innerText = "Please upload an image first.";
        return;
    }

    formData.append("file", fileInput);

    fetch("/process-image", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        handleImageResponse(data);
    })
    .catch(err => {
        console.error(err);
        imageResult.innerText = "Error processing image.";
    });
});

// Manual Text Analyze Section
document.getElementById("analyzeTextBtn").addEventListener("click", function () {
    const objectInput = document.getElementById("objectInput").value.trim();
    const formData = new FormData();
    const imageResult = document.getElementById("imageResult");

    if (!objectInput) {
        imageResult.innerText = "Please enter an object name.";
        return;
    }

    formData.append("manual_input", objectInput);

    fetch("/process-image", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        imageResult.innerText = data.response || data.error || "No response.";
        load3DModelFromObject(objectInput); // Load model manually too!
    })
    .catch(err => {
        console.error(err);
        imageResult.innerText = "Error processing text input.";
    });
});

// Function to Handle Image Response
function handleImageResponse(data) {
    const imageResult = document.getElementById("imageResult");

    if (data.multiple_objects) {
        imageResult.innerHTML = `<p>Detected multiple objects. Choose one:</p>`;
        data.multiple_objects.forEach(obj => {
            const btn = document.createElement("button");
            btn.innerText = obj;
            btn.style.margin = "5px";
            btn.onclick = () => {
                document.getElementById("objectInput").value = obj;
                load3DModelFromObject(obj); // Load model when clicked
            };
            imageResult.appendChild(btn);
        });
    } else {
        if (data.detected_object) {
            document.getElementById("objectInput").value = data.detected_object;
            load3DModelFromObject(data.detected_object); // Load detected model
        }
        imageResult.innerText = data.response || data.error || "No response.";
    }
}

// (🔥 Updated) Load 3D Model without clearing existing ones
function load3DModelFromObject(objectName) {
    const modelContainer = document.getElementById("modelViewerContainer");
    const formattedName = objectName.toLowerCase().replace(/\s+/g, "_");
    const modelPath = `/static/models/${formattedName}.glb`;

    // Check if the model is already loadeda
    const existingModel = modelContainer.querySelector(`model-viewer[src="${modelPath}"]`);
    if (existingModel) {
        console.log("Model already loaded:", modelPath);
        return; // Skip loading if the model is already present
    }

    // Create a loading message
    const loadingMessage = document.createElement("p");
    loadingMessage.innerText = `Loading ${objectName}...`;
    loadingMessage.style.fontSize = "1.2rem";
    loadingMessage.style.marginBottom = "10px";

    // Create a model-viewer
    const modelViewer = document.createElement("model-viewer");
    modelViewer.setAttribute("src", modelPath);
    modelViewer.setAttribute("alt", objectName);
    modelViewer.setAttribute("auto-rotate", "");
    modelViewer.setAttribute("camera-controls", "");
    modelViewer.style.width = "400px";
    modelViewer.style.height = "400px";

    modelContainer.appendChild(loadingMessage);
    modelContainer.appendChild(modelViewer);

    // Hide loading once model is loaded
    modelViewer.addEventListener('load', () => {
        loadingMessage.style.display = "none";
    });
}

// Optional: manual call function
function sendManualQuery(objectName) {
    const formData = new FormData();
    formData.append("manual_input", objectName);

    fetch("/process-image", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const result = data.response || data.error || "No response.";
        document.getElementById("imageResult").innerText = result;
        load3DModelFromObject(objectName);
    })
    .catch(err => {
        console.error(err);
        document.getElementById("imageResult").innerText = "Error processing selected object.";
    });
}

