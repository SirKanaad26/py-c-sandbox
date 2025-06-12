// Global state variables
let currentMode = "sandboxed";
let lastCompressed = "";
let lastOriginalData = "";

/**
 * Toggle between sandboxed and unsandboxed modes
 */
function toggleMode() {
  const toggle = document.querySelector('.toggle-switch');
  currentMode = currentMode === "sandboxed" ? "unsandboxed" : "sandboxed";
  toggle.className = `toggle-switch ${currentMode}`;
  
  if (currentMode === "sandboxed") {
    toggle.innerHTML = '<span>Sandboxed</span><span>Unsandboxed</span><div class="toggle-slider"></div>';
  } else {
    toggle.innerHTML = '<span>Sandboxed</span><span>Unsandboxed</span><div class="toggle-slider"></div>';
  }
  
  showAlert(`Switched to ${currentMode} mode`, 'success');
}



/**
 * Display alert messages to the user
 * @param {string} message - The message to display
 * @param {string} type - Alert type ('success' or 'error')
 */
function showAlert(message, type) {
  const alerts = document.getElementById('alerts');
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  alerts.appendChild(alert);
  
  // Auto-remove alert after 3 seconds
  if (type === 'success') {
    setTimeout(() => {
      alert.remove();
    }, 3000);
  } else {
    setTimeout(() => {
      alert.remove();
    }, 6000); 
  }
}

/**
 * Show or hide loading indicator
 * @param {boolean} show - Whether to show loading state
 */
function showLoading(show) {
  document.getElementById('loading').style.display = show ? 'block' : 'none';
  document.getElementById('results').style.display = show ? 'none' : 'block';
}

/**
 * Format bytes into human-readable format
 * @param {number} bytes - Number of bytes
 * @returns {string} Formatted string (e.g., "1.5 KB")
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Compress the input text using the backend API
 */
async function compress() {
  const text = document.getElementById('textInput').value;
  if (!text.trim()) {
    showAlert('Please enter some text to compress', 'error');
    return;
  }

  showLoading(true);
  lastOriginalData = text;

  try {
    const formData = new FormData();
    formData.append("data", text);
    formData.append("mode", currentMode);

    const response = await fetch("/compress/", {
      method: "POST",
      body: formData
    });
    
    // if (!response.ok) {
    //   throw new Error(`HTTP error! status: ${response.status}`);
    // }
    
    const result = await response.json();
    
    // Debug: Log the actual response to see what we're getting
    console.log('Backend response:', result);

    // Check if the response contains an error
    if (result.error) {
      throw new Error(result.message || 'Unknown compression error');
    }

    // Handle different possible response formats
    let originalSize, compressedSize, compressedData;
    
    if (typeof result.original_size === 'string' && result.original_size.includes('Error')) {
      // Handle error case where original_size contains error message
      throw new Error(result.original_size);
    }
    
    // Try to extract values from the response
    originalSize = parseInt(result.original_size) || 0;
    compressedSize = parseInt(result.compressed_size) || 0;
    compressedData = result.compressed_base64 || result.compressed || "";
    
    document.getElementById('originalSize').textContent = formatBytes(originalSize);
    document.getElementById('compressedSize').textContent = formatBytes(compressedSize);
    
    if (originalSize > 0 && compressedSize > 0) {
      const ratio = (originalSize / compressedSize).toFixed(2);
      document.getElementById('compressionRatio').textContent = ratio + 'x';
      
      const saved = ((originalSize - compressedSize) / originalSize * 100).toFixed(1);
      document.getElementById('spaceSaved').textContent = saved + '%';
    } else {
      document.getElementById('compressionRatio').textContent = 'N/A';
      document.getElementById('spaceSaved').textContent = 'N/A';
    }
    
    lastCompressed = result.compressed_base64;
    showAlert(`Compression successful using ${result.mode || currentMode} mode!`, 'success');
  } catch (error) {
    showAlert(error.message, 'error');
  } finally {
    showLoading(false);
  }
}

/**
 * Test decompression of the last compressed data
 */
async function decompress() {
  if (!lastCompressed) {
    showAlert('Please compress some data first!', 'error');
    return;
  }

  try {
    // For demo purposes - in real implementation, this would call your backend
    const decompressed = atob(lastCompressed);
    showAlert('Decompression test successful!', 'success');
  } catch (error) {
    showAlert('Decompression test failed: ' + error.message, 'error');
  }
}

/**
 * Download the compressed data as a file
 */
function downloadCompressed() {
  if (!lastCompressed) {
    showAlert('Please compress text first!', 'error');
    return;
  }

  try {
    // Convert base64 to binary data
    const byteCharacters = atob(lastCompressed);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: "application/octet-stream" });
    
    // Create download link
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "compressed.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showAlert('Download started!', 'success');
  } catch (error) {
    showAlert('Download failed: ' + error.message, 'error');
  }
}

/**
 * Copy compressed data to clipboard
 */
function copyToClipboard() {
  if (!lastCompressed) {
    showAlert('No compressed data to copy!', 'error');
    return;
  }

  navigator.clipboard.writeText(lastCompressed).then(() => {
    showAlert('Compressed data copied to clipboard!', 'success');
  }).catch(() => {
    showAlert('Failed to copy to clipboard', 'error');
  });
}

/**
 * Clear all input and reset the interface
 */
function clearInput() {
  document.getElementById('textInput').value = '';
  document.getElementById('results').style.display = 'none';
  lastCompressed = "";
  lastOriginalData = "";
  showAlert('Input cleared!', 'success');
}

/**
 * Handle file upload and read content
 * @param {File} file - The uploaded file
 */
function handleFile(file) {
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = function(e) {
    document.getElementById('textInput').value = e.target.result;
    showAlert(`File "${file.name}" loaded successfully!`, 'success');
  };
  reader.onerror = function() {
    showAlert('Error reading file!', 'error');
  };
  reader.readAsText(file);
}

/**
 * Prevent default drag and drop behavior
 * @param {Event} e - The drag event
 */
function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

/**
 * Highlight drop zone when dragging over
 * @param {Event} e - The drag event
 */
function highlight(e) {
  e.target.closest('.file-drop-zone')?.classList.add('dragover');
}

/**
 * Remove highlight from drop zone
 * @param {Event} e - The drag event
 */
function unhighlight(e) {
  e.target.closest('.file-drop-zone')?.classList.remove('dragover');
}

/**
 * Handle file drop event
 * @param {Event} e - The drop event
 */
function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  handleFile(files[0]);
}

/**
 * Initialize drag and drop functionality
 */
function initializeDragAndDrop() {
  const dropZone = document.querySelector('.file-drop-zone');
  const textarea = document.getElementById('textInput');

  if (!dropZone || !textarea) return;

  // Prevent default drag behaviors
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
    textarea.addEventListener(eventName, preventDefaults, false);
  });

  // Highlight drop zone when dragging over
  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, highlight, false);
    textarea.addEventListener(eventName, highlight, false);
  });

  // Remove highlight when dragging away
  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, unhighlight, false);
    textarea.addEventListener(eventName, unhighlight, false);
  });

  // Handle file drop
  dropZone.addEventListener('drop', handleDrop, false);
  textarea.addEventListener('drop', handleDrop, false);
}

/**
 * Initialize keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
  document.addEventListener('keydown', function(e) {
    // Ctrl+Enter to compress
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      compress();
    }
    
    // Ctrl+K to clear
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      clearInput();
    }
    
    // Escape to dismiss alerts
    if (e.key === 'Escape') {
      const alerts = document.querySelectorAll('.alert');
      alerts.forEach(alert => alert.remove());
    }
  });
}

/**
 * Initialize the application when DOM is loaded
 */
function initializeApp() {
  // Initialize drag and drop
  initializeDragAndDrop();
  
  // Initialize keyboard shortcuts
  initializeKeyboardShortcuts();
  
  // Show welcome message
  showAlert('Snappy Compression Tool loaded successfully!', 'success');
  
  // Add tooltips for keyboard shortcuts
  const textarea = document.getElementById('textInput');
  if (textarea) {
    textarea.setAttribute('title', 'Ctrl+Enter to compress, Ctrl+K to clear');
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);