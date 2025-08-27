# PII Detector Deployment Strategy

## Chosen Deployment Layer: Sidecar Container at API Routes Proxy
The PII solution will be deployed as a sidecar container alongside the API Routes Proxy (/api/*) in the backend. This proxy acts as a central gateway for routing requests to external services (e.g., Google Gemini, GitHub, TruffleHog CLI) and internal components (e.g., SOP Service, Database). The sidecar will intercept and process inbound/outbound data streams in real-time.

## Implementation Details

- **Container Setup:** Package the Python script into a lightweight Docker image (using Alpine base for minimal size). Run it as a sidecar in the same Kubernetes pod as the API proxy container.  
- **Integration Mechanism:** Use a shared volume or Unix socket for communication between the main container (Express.js) and sidecar. The sidecar listens for data (e.g., via a simple HTTP endpoint or log tailing) and applies detection/redaction before forwarding or logging.  

### Workflow:
1. Incoming requests/logs from Frontend or Analyzer UI pass through Auth Middleware to API Proxy.  
2. Sidecar scans JSON payloads or log strings for PII.  
3. If PII detected, redact and flag; otherwise, pass unchanged.  
4. Processed data proceeds to external tools or database.  

## Justification

- **Effectiveness:** Positioned at the application layer (API gateway), it catches PII at a choke point where data flows to unmonitored external integrations (as in the fraud incident). This prevents leaks in logs or plain-text storage in endpoints like /api/logs or Dashboard. Network-level (e.g., ingress controller) might miss internal traffic, while client-side (browser extension) wouldn't cover server logs.  
- **Scalability:** Scales horizontally with API pods in Kubernetes. As traffic increases, add replicas each with its own sidecar. No shared state needed, as processing is per-request.  
- **Latency:** Regex-based detection adds <5ms overhead per record. Sidecar runs in parallel, avoiding bottlenecks. For high-volume, optimize with async processing.  
- **Cost-Effectiveness:** Low resource use (CPU/Memory ~100m/128Mi per sidecar). No new infrastructure; leverages existing K8s cluster. Avoids expensive alternatives like dedicated service meshes (e.g., Istio with custom filters).  
- **Ease of Integration:** Minimal changes add sidecar to deployment YAML. Test via canary releases. Rollback is simple by removing the sidecar. Compatible with existing SSE for logs and MCF for backend.

## Alternatives Considered

- **DaemonSet:** Cluster-wide, good for network-level scanning, but overkill and higher latency for app-specific flows.  
- **API Gateway Plugin:** If using Kong/Nginx ingress, add as a plugin, but less flexible for custom Python logic.  
- **Browser Extension:** Client-side for UI rendering, but misses server-side leaks.  
- **Internal Tool Integration:** Embed in TruffleHog CLI, but limits scope to specific tools.  

---
