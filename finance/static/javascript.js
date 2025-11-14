let suggest = document.querySelector(".suggest_usernames");
let username = document.getElementById("username");

console.log("JavaScript loaded - elements:", {
    username: username,
    suggest: suggest,
    suggestParent: suggest ? suggest.parentElement : null
});

if (!username) {
    console.error("Username input not found!");
}

if (!suggest) {
    console.error("Suggest container not found!");
}

username.addEventListener("input", async function run() {
    let input = username.value.trim();
    console.log("Input value:", input);
    
    if (input.length < 1) {
        suggest.innerHTML = '';
        console.log("Input empty, clearing suggestions");
        return;
    }
    
    try {
        console.log("Sending request to /suggest with input:", input);
        let response = await fetch("/suggest", {
            method: "POST",
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({input: input})
        });
        
        console.log("Response status:", response.status);
        let result = await response.json();
        console.log("Server result:", result);

        let html = '';
        for (let i in result) {
            let item = result[i].username.replace(/</g, '&lt;').replace(/&/g, '&amp;');
            html += '<li class="suggested">' + item + '</li>';
        }
        
        console.log("Generated HTML with", result.length, "items");
        suggest.innerHTML = html;
        


        // Add click events to suggestions
        let suggested_user = document.querySelectorAll(".suggested");
        console.log("Adding click events to", suggested_user.length, "items");
        
        suggested_user.forEach(item => {
            item.addEventListener("click", () => {
                console.log("Clicked suggestion:", item.textContent);
                username.value = item.textContent;
                suggest.innerHTML = '';
            });
        });
        
    } catch (error) {
        console.error("Error in fetch:", error);
    }
});

// Hide suggestions when clicking outside
document.addEventListener('click', function(e) {
    if (e.target !== username && !suggest.contains(e.target)) {
        suggest.innerHTML = '';
        console.log("Cleared suggestions due to outside click");
    }
});

// Also hide on form submit
document.querySelector('form').addEventListener('submit', function() {
    suggest.innerHTML = '';
    console.log("Cleared suggestions on form submit");
});

console.log("Event listeners attached successfully");