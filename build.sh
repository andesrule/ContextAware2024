


cd backend
docker build -t riccardobenedetti/backend:latest -f Dockerfilebe .
docker push riccardobenedetti/backend:latest

cd ../frontend
docker build -t riccardobenedetti/frontend:latest -f Dockerfilefe .
docker push riccardobenedetti/frontend:latest

cd ../k8s
kubectl apply -f postgres-pvc.yml
kubectl apply -f db-deployment.yml
kubectl apply -f backend-deployment.yml
kubectl apply -f frontend-deployment.yml
echo "Deployment completed successfully!"
