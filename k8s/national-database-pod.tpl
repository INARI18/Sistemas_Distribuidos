apiVersion: v1
kind: Pod
metadata:
  name: ${NATIONAL_DB_NAME}
  labels:
    app: national-database
spec:
  containers:
    - name: national-db
      image: ${NATIONAL_DB_IMAGE}
      args: ["national-db", "${NATIONAL_DB_NAME}"]
  restartPolicy: Never
