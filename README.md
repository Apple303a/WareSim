# WareSim

Warehouse Management Simulator demonstrating Operating Systems concepts:
- File allocation: contiguous, linked and indexed allocation
- Free-space management
- Disk I/O scheduling: FCFS, SSTF, SCAN, C-SCAN, LOOK and C-LOOK
- Worker movement and performance comparison

## Team ownership

| Area | Owner | Folder |
|---|---|---|
| Storage management engine | Person 1 | `storage_engine/` |
| Warehouse scheduling engine | Person 2 | `scheduling_engine/` |
| Flask UI, integration and analytics | Person 3 | `app/` |

## Setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Open `http://127.0.0.1:5000`.

Using the virtual environment's Python directly avoids PowerShell execution
policy restrictions on `Activate.ps1`.

## Host on Google Cloud Run

The GitHub Actions workflow at `.github/workflows/deploy.yml` runs tests and
deploys to Cloud Run on every push to `main`. Local edits are not deployed
until they are committed and pushed to GitHub. No Docker installation is
needed locally; Cloud Run builds the source using the included `Dockerfile`.

One-time GCP setup (PowerShell with the Google Cloud SDK; project ID
`waresim`, region `asia-south1`):

1. Enable the Run, Cloud Build, Artifact Registry, and IAM Credentials APIs:

   ```powershell
   gcloud.cmd services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com iamcredentials.googleapis.com --project=waresim
   ```

2. Create a GitHub Actions Workload Identity Federation provider. Restrict it
   to this repository's `main` branch:

   ```powershell
   $PROJECT_NUMBER = gcloud.cmd projects describe waresim --format="value(projectNumber)"
   gcloud.cmd iam workload-identity-pools create github-pool --project=waresim --location=global --display-name="GitHub Actions"
   gcloud.cmd iam workload-identity-pools providers create-oidc github-provider --project=waresim --location=global --workload-identity-pool=github-pool --display-name="WareSim GitHub Actions" --issuer-uri="https://token.actions.githubusercontent.com" --attribute-mapping='google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref' --attribute-condition='assertion.repository == "Apple303a/WareSim" && assertion.ref == "refs/heads/main"'
   ```

3. Create a deployment service account and grant it Cloud Run deployment and
   source-build permissions:

   ```powershell
   gcloud.cmd iam service-accounts create github-deployer --project=waresim --display-name="GitHub Actions deployer"
   $DEPLOYER = "github-deployer@waresim.iam.gserviceaccount.com"
   gcloud.cmd projects add-iam-policy-binding waresim --member="serviceAccount:$DEPLOYER" --role="roles/run.admin" --condition=None
   gcloud.cmd projects add-iam-policy-binding waresim --member="serviceAccount:$DEPLOYER" --role="roles/cloudbuild.builds.editor" --condition=None
   gcloud.cmd projects add-iam-policy-binding waresim --member="serviceAccount:$DEPLOYER" --role="roles/artifactregistry.writer" --condition=None
   gcloud.cmd projects add-iam-policy-binding waresim --member="serviceAccount:$DEPLOYER" --role="roles/iam.serviceAccountUser" --condition=None
   gcloud.cmd iam service-accounts add-iam-policy-binding $DEPLOYER --project=waresim --role="roles/iam.workloadIdentityUser" --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/Apple303a/WareSim" --condition=None
   ```

4. In the GitHub repository, open **Settings → Secrets and variables → Actions
   → Variables** and add these repository variables:
   - `GCP_PROJECT_ID`: `waresim`
   - `GCP_REGION`: `asia-south1`
   - `GCP_DEPLOY_SERVICE_ACCOUNT`: `github-deployer@waresim.iam.gserviceaccount.com`
   - `GCP_WIF_PROVIDER`: `projects/255733592751/locations/global/workloadIdentityPools/github-pool/providers/github-provider`

After those variables are set, commit and push to `main`. GitHub Actions runs
the test suite and deploys the commit to Cloud Run. A deployment can also be
started once manually to publish the first URL:

```powershell
gcloud.cmd run deploy waresim --source . --project=waresim --region=asia-south1 --allow-unauthenticated --concurrency=1 --max=1 --memory=512Mi --cpu=1 --timeout=300
```

The workflow uses short-lived federated credentials rather than a stored
service-account key. The Cloud Run service is limited to one instance and one
concurrent request because WareSim keeps its state in memory. State is
temporary and can reset when the instance restarts or scales to zero. The
public service has no login, so anyone with its URL can change the shared demo
state. Cloud Run and build resources may incur charges.

## Try manual storage and operations

1. Open **Shipments**, choose one warehouse allocation model (contiguous,
   linked or indexed), and click **Set warehouse allocation model**.
2. Enter a unique ID, name, owner and size, then click **Create shipment**.
3. The success message shows allocated block positions. Follow **View updated
   dashboard** to see storage usage, the occupied-box map and shipment details.
   Use **Delete** in the dashboard shipment list to free a shipment's boxes.
4. Delete all shipments before changing the warehouse allocation model.
   Shipments are stored in memory only. Restarting the server resets the
   warehouse.
5. Open **Operations**, choose a shipment and READ/WRITE, then choose one
   scheduling algorithm or compare all six. Results include request order,
   movement and timing metrics.

The allocation model is selected once per warehouse and applies to all
shipments. Linked allocation chooses the first available boxes; it does not
randomize their positions. With free boxes in a row, those positions can look
sequential. To see linked blocks separated, create two small shipments, delete
the first, then create a shipment large enough to use boxes on both sides of the
remaining shipment.

## Run a controlled comparison

Open **Simulations** and choose **Run new demo** to generate a seeded workload
and run all 18 allocation/scheduling combinations. Each run shows the ordered
shipment lifecycle (create, delete, retain, replacement create) and the
shipment-level READ/WRITE transactions that expand into block requests.
Individual matrix cells can be rerun against that same workload. Choose a
comparison metric to see its best and worst successful pair; allocation
failures are called out separately. There is no single winner across every
metric.

The demo uses abstract time units, not seconds: moving one box costs 1 unit,
each block request has 1 unit of fixed latency, and transferring one 100-unit block costs
1 unit at the default rate. An I/O operation is a shipment-level READ/WRITE;
it creates one request per block in that shipment. Operations arrive at
different simulated times over the first 100 time units. Use **Run new demo**
to increment the seed and compare a different workload. External fragmentation
is the free-box count outside the largest contiguous free extent; it matters
most for contiguous allocation.

## Shared rules

1. Use Python dictionaries/lists with the field names defined in `shared/contracts.py`.
2. Box positions are zero-based integers: `0, 1, 2, ...`.
3. One box stores exactly one block; one block belongs to exactly one shipment.
4. Each shipment-level operation expands into one request per required block.
5. The scheduler receives physical integer positions, never shipment IDs alone.
6. Keep the two engines independent of Flask. The UI calls their public functions.
7. Compare algorithms on identical workloads, arrival times and initial worker positions.

## Current status

Storage allocation, manual operations, and reproducible allocation/scheduling
experiments are wired to the UI. The project is a textbook model, not a faithful
simulation of a named modern filesystem or measured disk hardware.
See `docs/TEAM_WORK_SPLIT.md` and `docs/CONTRACTS.md` for the project split and
shared data conventions.
