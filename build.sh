cd backend
docker build -t riccardobenedetti/backend:latest -f Dockerfilebe .
docker push riccardobenedetti/backend:latest

cd ../frontend
docker build -t riccardobenedetti/frontend:latest -f Dockerfilefe .
docker push riccardobenedetti/frontend:latest

cd ../k8s
kubectl apply -f postgres-pvc.yml --validate=false
kubectl apply -f db-deployment.yml --validate=false
kubectl apply -f backend-deployment.yml --validate=false
kubectl apply -f frontend-deployment.yml --validate=false

