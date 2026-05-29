apiVersion: v1
kind: Pod
metadata:
  name: ${HEALTH_POST_NAME}
  labels:
    app: health-post
    post-id: "${HEALTH_POST_ID}"
spec:
  containers:
    - name: health-post
      image: ${HEALTH_POST_IMAGE}
      args: ["health-post", "${HEALTH_POST_ID}"]
  restartPolicy: Never
