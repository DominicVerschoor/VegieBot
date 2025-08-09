<?php
/**
 * Debug Chatbot Handler - with error logging and debugging
 * Place this file in includes/bot_handler.php
 */

// Enable error logging to file instead of displaying
ini_set('display_errors', 0);
ini_set('log_errors', 1);
ini_set('error_log', dirname(__FILE__) . '/chatbot_errors.log');

// Start session for basic rate limiting
session_start();

// Set headers FIRST - before any output
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Function to send JSON response and exit
function sendJsonResponse($data, $httpCode = 200) {
    http_response_code($httpCode);
    echo json_encode($data);
    exit;
}

// Function to log errors
function logError($message) {
    error_log("Chatbot Error: " . $message);
}

try {
    // Only allow POST requests
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        sendJsonResponse(['error' => 'Method not allowed'], 405);
    }

    // Basic rate limiting (2 seconds between requests)
    if (!isset($_SESSION['chatbot_last_request'])) {
        $_SESSION['chatbot_last_request'] = 0;
    }

    $now = time();
    if ($now - $_SESSION['chatbot_last_request'] < 2) {
        sendJsonResponse(['error' => 'Please wait a moment before sending another message'], 429);
    }
    $_SESSION['chatbot_last_request'] = $now;

    // Get and validate input
    $rawInput = file_get_contents('php://input');
    logError("Raw input received: " . $rawInput);

    $input = json_decode($rawInput, true);

    if (json_last_error() !== JSON_ERROR_NONE) {
        logError("JSON decode error: " . json_last_error_msg());
        sendJsonResponse(['error' => 'Invalid JSON input'], 400);
    }

    if (!isset($input['message']) || empty(trim($input['message']))) {
        sendJsonResponse(['error' => 'Message is required'], 400);
    }

    $userMessage = trim($input['message']);
    logError("Processing message: " . $userMessage);

    // Validate message length
    if (strlen($userMessage) > 500) {
        sendJsonResponse(['error' => 'Message too long (max 500 characters)'], 400);
    }

    // Sanitize message (basic XSS prevention)
    $userMessage = htmlspecialchars($userMessage, ENT_QUOTES, 'UTF-8');

    // Prepare data to send to Render backend
    $postData = json_encode(['message' => $userMessage]);
    logError("Sending to backend: " . $postData);

    // Check if cURL is available
    if (!function_exists('curl_init')) {
        logError("cURL is not available on this server");
        sendJsonResponse(['error' => 'Server configuration error: cURL not available'], 500);
    }

    // Initialize cURL
    $ch = curl_init();

    // Set cURL options
    curl_setopt_array($ch, [
        CURLOPT_URL => 'https://vegiebot.onrender.com/chat',
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $postData,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Content-Length: ' . strlen($postData),
            'User-Agent: AccessiMarket-Chatbot/1.0'
        ],
        CURLOPT_TIMEOUT => 30, // 30 second timeout
        CURLOPT_CONNECTTIMEOUT => 10, // 10 second connection timeout
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS => 3
    ]);

    // Execute the request
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);

    logError("Backend HTTP Code: " . $httpCode);
    logError("Backend Response: " . substr($response, 0, 200) . (strlen($response) > 200 ? '...' : ''));

    curl_close($ch);

    // Handle cURL errors
    if ($error) {
        logError("cURL Error: " . $error);
        sendJsonResponse(['error' => 'Unable to connect to the chatbot service. Please try again later.'], 500);
    }

    // Handle HTTP errors
    if ($httpCode !== 200) {
        logError("HTTP Error: " . $httpCode . " - Response: " . substr($response, 0, 500));
        
        if ($httpCode >= 500) {
            sendJsonResponse(['error' => 'The chatbot service is temporarily unavailable. Please try again later.'], 503);
        } else {
            sendJsonResponse(['error' => 'There was an issue processing your request. Please try again.'], 502);
        }
    }

    // Decode and validate response
    $responseData = json_decode($response, true);

    if (json_last_error() !== JSON_ERROR_NONE) {
        logError("Backend JSON Error: " . json_last_error_msg() . " - Response: " . substr($response, 0, 500));
        sendJsonResponse(['error' => 'Received an invalid response from the chatbot service.'], 502);
    }

    // Validate response structure
    if (!isset($responseData['reply'])) {
        logError("Backend Response Error: Missing 'reply' field - Response: " . print_r($responseData, true));
        sendJsonResponse(['error' => 'Received an incomplete response from the chatbot service.'], 502);
    }

    // Sanitize the response
    $responseData['reply'] = htmlspecialchars($responseData['reply'], ENT_QUOTES, 'UTF-8');

    // Log successful interaction
    logError("Success: Response length: " . strlen($responseData['reply']));

    // Return the response
    sendJsonResponse($responseData);

} catch (Exception $e) {
    logError("Unexpected error: " . $e->getMessage() . " in " . $e->getFile() . " line " . $e->getLine());
    sendJsonResponse(['error' => 'An unexpected error occurred. Please try again later.'], 500);
} catch (Error $e) {
    logError("Fatal error: " . $e->getMessage() . " in " . $e->getFile() . " line " . $e->getLine());
    sendJsonResponse(['error' => 'A fatal error occurred. Please try again later.'], 500);
}
?>