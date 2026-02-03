// --- DOM ELEMENTS: MAIN UI ---
const scenarioInput = document.getElementById('scenarioInput');
const startDebateBtn = document.getElementById('startDebate');
const thesisContent = document.getElementById('thesisContent');
const antithesisContent = document.getElementById('antithesisContent');
const synthesisContent = document.getElementById('synthesisContent');
const thesisStatus = document.getElementById('thesisStatus');
const antithesisStatus = document.getElementById('antithesisStatus');
const synthesisStatus = document.getElementById('synthesisStatus');
const riskGrid = document.getElementById('riskGrid');
const confidenceBar = document.getElementById('confidenceBar');
const confidenceValue = document.getElementById('confidenceValue');

// --- DOM ELEMENTS FOR DOWNLOAD ---
const btnDownloadWord = document.getElementById('btnDownloadWord');
const btnDownloadMd = document.getElementById('btnDownloadMd');

// STORE DEBATE DATA GLOBALLY
let currentDebateData = null;

// ABORT CONTROLLER FOR CANCELLING REQUESTS
let currentAbortController = null;


// ==========================================
//  DOWNLOAD LOGIC (FIXED VERSION)
// ==========================================

function triggerDownload(type) {
    console.log(`[Download] Triggered for type: ${type}`);

    if (!currentDebateData) {
        alert("Please start a debate first to generate a report.");
        return;
    }

    try {
        const topic = scenarioInput.value || "Cogito_Report";
        // Clean filename to avoid OS errors
        const cleanName = topic.replace(/[^a-z0-9]/gi, '_').substring(0, 30);
        
        // --- SAFE DATA EXTRACTION ---
        const getPoints = (agent) => {
            if (currentDebateData[agent] && Array.isArray(currentDebateData[agent].points)) {
                return currentDebateData[agent].points;
            }
            return ["No points generated."];
        };

        const getTitle = (agent) => {
             return currentDebateData[agent]?.title || `${agent} Argument`;
        };

        const getRisks = () => {
            if (Array.isArray(currentDebateData.risks)) {
                return currentDebateData.risks;
            }
            return [{ severity: "unknown", title: "No Risks", desc: "None identified." }];
        };

        const thesisPoints = getPoints('thesis');
        const thesisTitle = getTitle('thesis');
        const antiPoints = getPoints('antithesis');
        const antiTitle = getTitle('antithesis');
        const risks = getRisks();
        const synthesisRec = currentDebateData.synthesis?.recommendation || "No verdict.";
        const synthesisSum = currentDebateData.synthesis?.summary || "No summary.";

        let content = "";
        let mimeType = "";
        let extension = "";
        let fullFileName = "";

        if (type === 'md') {
            // MARKDOWN
            const tPointsStr = thesisPoints.map(p => `- ${p}`).join('\n');
            const aPointsStr = antiPoints.map(p => `- ${p}`).join('\n');
            const rStr = risks.map(r => `**[${r.severity.toUpperCase()}] ${r.title}:** ${r.desc}`).join('\n\n');

            content = `# Cogito Requiem Report: ${topic}\n\n` +
                      `## 1. Thesis (Cogito)\n**${thesisTitle}**\n${tPointsStr}\n\n` +
                      `## 2. Antithesis (Requiem)\n**${antiTitle}**\n${aPointsStr}\n\n` +
                      `## 3. Synthesis (Verdict)\n**Verdict:** ${synthesisRec}\n\n` +
                      `> ${synthesisSum}\n\n` +
                      `## 4. Risks Identified\n${rStr}`;
            
            mimeType = "text/markdown;charset=utf-8";
            extension = "md";

        } else {
            // WORD (HTML)
            const tList = thesisPoints.map(p => `<li>${p}</li>`).join('');
            const aList = antiPoints.map(p => `<li>${p}</li>`).join('');
            const rList = risks.map(r => `<li style="margin-bottom: 10px;"><strong>[${r.severity.toUpperCase()}] ${r.title}:</strong> ${r.desc}</li>`).join('');

            content = `
                <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
                <head><meta charset='utf-8'><title>Report</title></head>
                <body style="font-family: Arial, sans-serif; line-height: 1.5;">
                    <h1 style="color: #333;">Cogito Requiem Report: ${topic}</h1>
                    <hr>
                    <h2 style="color: #22d3ee;">1. Thesis (Cogito)</h2>
                    <h3>${thesisTitle}</h3>
                    <ul>${tList}</ul>
                    <h2 style="color: #f472b6;">2. Antithesis (Requiem)</h2>
                    <h3>${antiTitle}</h3>
                    <ul>${aList}</ul>
                    <h2 style="color: #a78bfa;">3. Synthesis (Curator)</h2>
                    <div style="background: #f5f5f5; padding: 15px; border-left: 5px solid #a78bfa;">
                        <p><strong>Verdict:</strong> ${synthesisRec}</p>
                        <p><em>${synthesisSum}</em></p>
                    </div>
                    <h2 style="color: #fbbf24;">4. Risks Identified</h2>
                    <ul>${rList}</ul>
                </body></html>
            `;
            mimeType = "application/msword";
            extension = "doc";
        }

        fullFileName = `${cleanName}.${extension}`;

        // === IMPROVED DOWNLOAD METHOD ===
        const blob = new Blob([content], { type: mimeType });
        
        // Method 1: Use modern download API if available
        if (window.navigator && window.navigator.msSaveOrOpenBlob) {
            // For IE/Edge Legacy
            window.navigator.msSaveOrOpenBlob(blob, fullFileName);
        } else {
            // Modern browsers
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = fullFileName;
            link.style.display = 'none';
            
            // Append to body (required for Firefox)
            document.body.appendChild(link);
            
            // Trigger click
            link.click();
            
            // Cleanup after a short delay
            setTimeout(() => {
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }, 250);
        }
        
        showDownloadToast(fullFileName);
        console.log(`[Download] Successfully initiated download for: ${fullFileName}`);

    } catch (error) {
        console.error("Download Error:", error);
        alert("Error generating download: " + error.message);
    }
}

// Toast Notification (Fixed)
function showDownloadToast(fileName) {
    // Remove any existing toast
    const existingToast = document.querySelector('.download-toast');
    if (existingToast) existingToast.remove();
    
    const toast = document.createElement('div');
    toast.className = 'download-toast';
    toast.innerHTML = `<span>✓ Downloaded: ${fileName}</span>`;
    toast.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: linear-gradient(135deg, #1a1f2e, #2a2f3e);
        border: 1px solid #22c55e;
        color: #fff;
        padding: 15px 25px;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        z-index: 3000;
        font-family: inherit;
        font-size: 0.9rem;
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// === ATTACH EVENT LISTENERS ===
document.addEventListener('DOMContentLoaded', function() {
    // Re-query elements after DOM is ready (belt and suspenders approach)
    const wordBtn = document.getElementById('btnDownloadWord');
    const mdBtn = document.getElementById('btnDownloadMd');
    
    if (wordBtn) {
        wordBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("Word button clicked!");
            triggerDownload('word');
        });
        console.log("✓ Word download button connected.");
    } else {
        console.error("✗ Word download button NOT found!");
    }

    if (mdBtn) {
        mdBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("MD button clicked!");
            triggerDownload('md');
        });
        console.log("✓ MD download button connected.");
    } else {
        console.error("✗ MD download button NOT found!");
    }
});


// ==========================================
//  EXISTING DEBATE LOGIC
// ==========================================

function formatAgentResponse(title, points) {
    let html = `<strong>${title}</strong><ul class="agent-points">`;
    if(Array.isArray(points)) {
        points.forEach(point => html += `<li>${point}</li>`);
    } else {
        html += `<li>${points}</li>`;
    }
    html += '</ul>';
    return html;
}

function renderRisks(risks) {
    if(!risks || risks.length === 0) {
        riskGrid.innerHTML = '<p class="placeholder-text">No significant risks identified.</p>';
        return;
    }
    riskGrid.innerHTML = risks.map(risk => `
        <div class="risk-item">
            <div class="risk-severity ${risk.severity}"></div>
            <div class="risk-text">
                <strong>${risk.title}</strong>
                ${risk.desc}
            </div>
        </div>
    `).join('');
}

function animateConfidence(value) {
    confidenceBar.style.width = '0%';
    confidenceValue.textContent = '0%';
    
    setTimeout(() => {
        confidenceBar.style.width = `${value}%`;
        let current = 0;
        const increment = value / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= value) {
                current = value;
                clearInterval(timer);
            }
            confidenceValue.textContent = `${Math.round(current)}%`;
        }, 20);
    }, 500);
}

async function runDebate() {
    const userInput = scenarioInput.value.trim();
    if (!userInput) {
        scenarioInput.style.borderColor = '#ef4444';
        scenarioInput.placeholder = 'Please enter a decision scenario...';
        setTimeout(() => {
            scenarioInput.style.borderColor = '';
            scenarioInput.placeholder = 'e.g., Should we adopt a Microservices architecture or stick to a Monolith?';
        }, 2000);
        return;
    }
    
    thesisContent.innerHTML = '<p class="placeholder-text">Cogito is analyzing the scenario...</p>';
    antithesisContent.innerHTML = '<p class="placeholder-text">Requiem is preparing counter-arguments...</p>';
    synthesisContent.innerHTML = '<p class="placeholder-text">Curator will synthesize after debate...</p>';
    riskGrid.innerHTML = '<p class="placeholder-text">Scanning for risks...</p>';
    confidenceBar.style.width = '0%';
    confidenceValue.textContent = '—';
    
    // Create new abort controller for this request
    currentAbortController = new AbortController();
    
    startDebateBtn.disabled = true;
    scenarioInput.disabled = true;
    
    // Change button to Cancel mode
    startDebateBtn.textContent = '⏹ Cancel Debate';
    startDebateBtn.disabled = false;
    startDebateBtn.classList.add('cancel-mode');
    startDebateBtn.onclick = cancelDebate;
    
    thesisStatus.className = 'agent-status';
    antithesisStatus.className = 'agent-status';
    synthesisStatus.className = 'agent-status';
    
    // Show thinking status
    thesisStatus.className = 'agent-status thinking';
    
    try {
        const response = await fetch('http://localhost:8000/api/debate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: userInput }),
            signal: currentAbortController.signal
        });

        if (!response.ok) throw new Error('API Error');
        const debate = await response.json();
        
        // SAVE DATA FOR DOWNLOADS
        currentDebateData = debate;
        console.log("Debate Data Received:", currentDebateData); 

        thesisStatus.className = 'agent-status thinking';
        await new Promise(r => setTimeout(r, 500));
        const thesisHTML = formatAgentResponse(debate.thesis.title, debate.thesis.points);
        thesisContent.innerHTML = thesisHTML;
        thesisStatus.className = 'agent-status complete';
        
        antithesisStatus.className = 'agent-status thinking';
        await new Promise(r => setTimeout(r, 800));
        const antithesisHTML = formatAgentResponse(debate.antithesis.title, debate.antithesis.points);
        antithesisContent.innerHTML = antithesisHTML;
        antithesisStatus.className = 'agent-status complete';
        
        await new Promise(r => setTimeout(r, 500));
        renderRisks(debate.risks);
        
        synthesisStatus.className = 'agent-status thinking';
        await new Promise(r => setTimeout(r, 800));
        const synthesisHTML = `
            <div class="synthesis-result">
                <strong>Recommendation: ${debate.synthesis.recommendation}</strong>
                <p>${debate.synthesis.summary}</p>
            </div>
        `;
        synthesisContent.innerHTML = synthesisHTML;
        synthesisStatus.className = 'agent-status complete';
        
        await new Promise(r => setTimeout(r, 500));
        animateConfidence(debate.synthesis.confidence);
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Debate cancelled by user');
            thesisContent.innerHTML = '<p class="placeholder-text" style="color: #fbbf24;">Debate cancelled.</p>';
            antithesisContent.innerHTML = '<p class="placeholder-text">—</p>';
            synthesisContent.innerHTML = '<p class="placeholder-text">—</p>';
            thesisStatus.className = 'agent-status';
            antithesisStatus.className = 'agent-status';
            synthesisStatus.className = 'agent-status';
        } else {
            console.error('Debate error:', error);
            thesisContent.innerHTML = '<p class="placeholder-text" style="color: #ef4444;">Error: Is the Python backend (api.py) running?</p>';
            startDebateBtn.textContent = 'Connection Failed';
        }
    } finally {
        resetDebateButton();
    }
}

// Cancel the current debate
async function cancelDebate() {
    console.log('Cancelling debate...');
    
    // Abort the fetch request
    if (currentAbortController) {
        currentAbortController.abort();
    }
    
    // Also tell the backend to cancel (in case it's still processing)
    try {
        await fetch('http://localhost:8000/api/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (e) {
        // Ignore errors - backend might not be reachable
    }
    
    resetDebateButton();
}

// Reset the debate button to its normal state
function resetDebateButton() {
    startDebateBtn.disabled = false;
    scenarioInput.disabled = false;
    startDebateBtn.textContent = 'Start New Debate';
    startDebateBtn.classList.remove('cancel-mode');
    startDebateBtn.onclick = runDebate;
    currentAbortController = null;
}

// Event listeners for debate
if (scenarioInput) {
    scenarioInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !startDebateBtn.disabled) {
            runDebate();
        }
    });
}

if (startDebateBtn) {
    startDebateBtn.addEventListener('click', runDebate);
}

// Visual Helpers - Smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
});

// Intersection Observer for animations
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add('in-view');
    });
}, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

document.querySelectorAll('.section').forEach(section => observer.observe(section));

// Dynamic CSS injection for Agents
const style = document.createElement('style');
style.textContent = `
    .agent-points { list-style: none; margin: 12px 0 0 0; padding: 0; }
    .agent-points li { position: relative; padding-left: 20px; margin-bottom: 12px; color: var(--text-secondary); line-height: 1.6; }
    .agent-points li::before { content: '→'; position: absolute; left: 0; color: var(--text-muted); }
    .synthesis-result { background: linear-gradient(135deg, rgba(167, 139, 250, 0.1), transparent); padding: 20px; border-radius: 8px; border-left: 3px solid var(--synthesis-color); }
    .synthesis-result strong { display: block; color: var(--synthesis-color); margin-bottom: 12px; font-size: 1.05rem; }
    .section { opacity: 0; transform: translateY(20px); transition: opacity 0.6s ease, transform 0.6s ease; }
    .section.in-view { opacity: 1; transform: translateY(0); }
    
    /* Cancel button styling */
    .btn.cancel-mode {
        background: linear-gradient(135deg, #ef4444, #dc2626) !important;
        color: white !important;
        border: none !important;
        animation: pulse-cancel 1.5s ease infinite;
    }
    .btn.cancel-mode:hover {
        background: linear-gradient(135deg, #dc2626, #b91c1c) !important;
        transform: translateY(-2px);
        box-shadow: 0 10px 40px rgba(239, 68, 68, 0.3);
    }
    @keyframes pulse-cancel {
        0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
    }
`;
document.head.appendChild(style);

console.log('%c🎭 Cogito Requiem (Connected)', 'font-size: 20px; font-weight: bold; color: #a78bfa;');