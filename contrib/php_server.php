<?php
define("DESTINATION", "/var/www/reports"); // Should be writable by www-data
define("MAX_SIZE", 524288); // 512 KiB

define("DATE_FORMAT", "/^[0-9]{2,12}\\.[0-9]{1,3}\$/");

function store($report, $address) {
    $now = microtime(TRUE);
    $secs = (int) $now;
    $msecs = ((int) ($now * 1000)) % 1000;

    // Find a filename that doesn't already exist
    while(TRUE) {
        $submitted_date = sprintf("%d.%03d", $secs, $msecs);
        $filename = "report_" . $submitted_date . ".txt";
        if(DESTINATION !== "") {
            $filename = DESTINATION . "/" . $filename;
        }
        if(!file_exists($filename)) {
            break;
        }
        $msecs += 1;
    }

    // Go over lines to make sure there's a date
    $lines = explode("\n", $report);
    $count = count($lines);
    for($i = 0; $i < $count; $i++) {
        if(substr($lines[$i], 0, 5) == "date:") {
            $date = substr($lines[$i], 5);
            if(preg_match(DATE_FORMAT, $date)) {
                $fp = fopen($filename, "wb");
                fwrite($fp, "submitted_from:" . $address . "\n");
                fwrite($fp, "submitted_date:" . $submitted_date . "\n");
                fwrite($fp, $report);
                fclose($fp);
                return NULL;
            } else {
                return "invalid date";
            }
        }
    }
    return "missing date field";
}

// Reject non-POST requests
if($_SERVER["REQUEST_METHOD"] !== "POST") {
    header("HTTP/1.1 403 Forbidden");
    header("Content-Type: text/plain");
    echo("Invalid request");
    exit();
}

// Get the posted input
if(!isset($_SERVER["CONTENT_LENGTH"]) ||
    ((int) $_SERVER["CONTENT_LENGTH"]) > MAX_SIZE)
{
    header("HTTP/1.1 403 Forbidden");
    header("Content-Type: text/plain");
    echo("report too big" . " " . $_SERVER["CONTENT_LENGTH"]);
    var_dump($_SERVER["CONTENT_LENGTH"]);
    exit();
}
$request_body = file_get_contents("php://input");

// Try to store
$response_body = store($request_body, $_SERVER['REMOTE_ADDR']);
if(!$response_body) {
    header("Content-Type: text/plain");
    echo("stored");
} else {
    header("HTTP/1.1 500 Server Error");
    header("Content-Type: text/plain");
    echo($response_body);
}
?>
