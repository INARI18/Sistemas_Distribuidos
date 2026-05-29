apiVersion: v1
kind: Pod
metadata:
  name: ${PATIENT_NAME}
  labels:
    app: patient
    patient-id: "${PATIENT_ID}"
spec:
  containers:
    - name: patient
      image: ${PATIENT_IMAGE}
      args: ["patient", "${PATIENT_ID}"]
  restartPolicy: Never
