<?php
// This is vulnerable to RCE attacks
$upload_dir = 'uploads/';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_FILES['file'])) {
        die('No file uploaded.');
    }

    $file = $_FILES['file'];

    // 1. No filename sanitization
    $filename = $file['name'];

    // 2. No file extension or content validation
    $target_file = $upload_dir . $filename;

    // 3. Directly moving uploaded file without security checks
    if (move_uploaded_file($file['tmp_name'], $target_file)) {
        echo 'File uploaded successfully: ' . $target_file;
    } else {
        echo 'File upload failed.';
    }
}

?>

<!doctype html>
<html lang="en">
<head>
    <title>Upload File</title>
</head>
<body>
    <h1>Upload File</h1>
    <form action="" method="post" enctype="multipart/form-data">
        <p><input type="file" name="file" /></p>
        <p><input type="submit" value="Upload" /></p>
    </form>
</body>
</html>
