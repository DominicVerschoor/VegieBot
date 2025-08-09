<?php
/**
 * Direct test script for chatbot handler
 * Place this in your website root and access via browser
 */

echo "<h2>Chatbot Handler Test</h2>";

// Test 1: Check if chatbot_handler.php exists
$handlerPath = 'includes/bot_handler.php';
if (!file_exists($handlerPath)) {
    echo "<p style='color: red;'>❌ ERROR: bot_handler.php not found at: $handlerPath</p>";
    echo "<p>Make sure you've placed the file in the correct location.</p>";
    exit;
}

echo "<p style='color: green;'>✅ bot_handler.php found</p>";

// Test 2: Check if cURL is available
if (!function_exists('curl_init')) {
    echo "<p style='color: red;'>❌ ERROR: cURL is not available on this server</p>";
    echo "<p>Contact your hosting provider to enable cURL</p>";
    exit;
}

echo "<p style='color: green;'>✅ cURL is available</p>";

// Test 3: Test the handler directly
echo "<h3>Testing Chatbot Handler...</h3>";

$testMessage = "This is a test message, respond with 'MESSAGE RECIEVED NO PROBLEMS!'";
$postData = json_encode(['message' => $testMessage]);

$context = stream_context_create([
    'http' => [
        'method' => 'POST',
        'header' => "Content-Type: application/json\r\nContent-Length: " . strlen($postData),
        'content' => $postData
    ]
]);

// Get the full URL to your chatbot handler
$handlerUrl = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? 'https' : 'http') . 
              '://' . $_SERVER['HTTP_HOST'] . 
              dirname($_SERVER['REQUEST_URI']) . '/' . $handlerPath;

echo "<p>Testing URL: <code>$handlerUrl</code></p>";

$response = @file_get_contents($handlerUrl, false, $context);

if ($response === FALSE) {
    echo "<p style='color: red;'>❌ ERROR: Could not reach chatbot handler</p>";
    echo "<p>Check file permissions and server configuration</p>";
    
    // Check error details
    $error = error_get_last();
    if ($error) {
        echo "<p><strong>Error details:</strong> " . htmlspecialchars($error['message']) . "</p>";
    }
} else {
    echo "<p style='color: green;'>✅ Chatbot handler responded</p>";
    echo "<p><strong>Response:</strong></p>";
    echo "<pre style='background: #f0f0f0; padding: 10px; border-radius: 5px;'>" . htmlspecialchars($response) . "</pre>";
    
    // Try to decode JSON
    $decoded = json_decode($response, true);
    if (json_last_error() === JSON_ERROR_NONE) {
        echo "<p style='color: green;'>✅ Valid JSON response</p>";
        if (isset($decoded['reply'])) {
            echo "<p style='color: green;'>✅ Contains 'reply' field</p>";
        } else {
            echo "<p style='color: orange;'>⚠️ Missing 'reply' field</p>";
        }
    } else {
        echo "<p style='color: red;'>❌ Invalid JSON: " . json_last_error_msg() . "</p>";
        echo "<p>This suggests there's a PHP error or the wrong content is being returned</p>";
    }
}

// Test 4: Check if we can reach the Render backend directly
echo "<h3>Testing Render Backend Connection...</h3>";

$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL => 'https://vegiebot.onrender.com/chat',
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $postData,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Content-Length: ' . strlen($postData)
    ],
    CURLOPT_TIMEOUT => 30,
    CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_SSL_VERIFYPEER => true
]);

$backendResponse = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlError = curl_error($ch);
curl_close($ch);

if ($curlError) {
    echo "<p style='color: red;'>❌ cURL Error: " . htmlspecialchars($curlError) . "</p>";
} else {
    echo "<p style='color: green;'>✅ Successfully connected to Render backend</p>";
    echo "<p><strong>HTTP Code:</strong> $httpCode</p>";
    echo "<p><strong>Response:</strong></p>";
    echo "<pre style='background: #f0f0f0; padding: 10px; border-radius: 5px;'>" . htmlspecialchars(substr($backendResponse, 0, 500)) . "</pre>";
}

// Test 5: Check error log
echo "<h3>Checking Error Logs...</h3>";
$errorLogPath = 'includes/chatbot_errors.log';
if (file_exists($errorLogPath)) {
    $errorLog = file_get_contents($errorLogPath);
    if (!empty($errorLog)) {
        echo "<p><strong>Recent errors:</strong></p>";
        echo "<pre style='background: #fff0f0; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;'>" . htmlspecialchars($errorLog) . "</pre>";
    } else {
        echo "<p style='color: green;'>✅ No errors in log file</p>";
    }
} else {
    echo "<p>ℹ️ No error log file found (this is normal if no errors occurred)</p>";
}

echo "<hr>";
echo "<p><strong>Next steps:</strong></p>";
echo "<ul>";
echo "<li>If all tests pass, the chatbot should work</li>";
echo "<li>If there are errors, check the specific error messages above</li>";
echo "<li>Make sure your Render backend is running and accessible</li>";
echo "<li>Check file permissions on your hosting server</li>";
echo "</ul>";
?>