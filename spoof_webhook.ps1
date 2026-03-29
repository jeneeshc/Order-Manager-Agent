$url = "https://order-manager-agent-275859621740.europe-west1.run.app/webhook"
$headers = @{"Content-Type" = "application/json"}
$body = @{
    "object" = "whatsapp_business_account"
    "entry" = @(
        @{
            "id" = "1457897545971090"
            "changes" = @(
                @{
                    "value" = @{
                        "messaging_product" = "whatsapp"
                        "metadata" = @{
                            "display_phone_number" = "15551556765"
                            "phone_number_id" = "1094575157063755"
                        }
                        "messages" = @(
                            @{
                                "from" = "918289897413"
                                "id" = "wamid.HBgLOTE4Mjg5ODk3NDEzFQIAEhgUM0ZBNkExMzNBM0M0MkY1MjY0NkIA"
                                "timestamp" = "1711730000"
                                "text" = @{
                                    "body" = "Can I get 15000 stitches on velvet please?"
                                }
                                "type" = "text"
                            }
                        )
                    }
                    "field" = "messages"
                }
            )
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body $body
    Write-Host "HTTP 200 Fast Response (Webhook Pinged Successfully):"
    $response | ConvertTo-Json
    Start-Sleep -Seconds 12
    Write-Host "Fetching background LangGraph traces..."
    gcloud logging read 'resource.labels.service_name="order-manager-agent"' --project ai-agent-462312 --limit 50 --format json > prod_logs_v9.json
    Get-Content prod_logs_v9.json | Select-String "textPayload|message" -Context 2 > filtered_v9.txt
    Get-Content filtered_v9.txt | Select-Object -Last 40
} catch {
    Write-Host "Crash: $_"
}
