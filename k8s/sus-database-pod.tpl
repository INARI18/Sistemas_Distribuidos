apiVersion: v1
kind: Pod
metadata:
  name: ${SUS_DB_NAME}
  labels:
    app: sus-database
spec:
  containers:
    - name: sus-db
      image: ${SUS_DB_IMAGE}
      args: ["sus-db", "${SUS_DB_NAME}"]
  restartPolicy: Never
