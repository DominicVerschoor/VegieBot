<?php
$message = "What is the population of Amsterdam?";
$ch = curl_init('https://your-render-app.onrender.com/chat');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(['message' => $message]));

$response = curl_exec($ch);
curl_close($ch);

$data = json_decode($response, true);
echo $data['reply'];
?>
