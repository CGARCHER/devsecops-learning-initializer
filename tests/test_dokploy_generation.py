import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from devsecops_initializer.service import InitializerService

class DokployGenerationTests(unittest.TestCase):
    def test_files_and_explanations_are_generated_without_dashboard_or_compose(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'pom.xml').write_text('<project><parent><artifactId>spring-boot-starter-parent</artifactId></parent></project>')
            service=InitializerService()
            plan=service.analyze(root)
            descriptions={c.path:c.reason for c in plan.changes}
            self.assertIn('inactivo',descriptions['.github/workflows/deploy-dokploy.yml'])
            self.assertIn('commit autorizado',descriptions['.devsecops/engine/scripts/deploy_dokploy.cjs'])
            self.assertIn('secreto',descriptions['SECURITY_SETUP.md'])
            with zipfile.ZipFile(io.BytesIO(service.generate_zip(root))) as archive:
                self.assertIn('.devsecops/engine/scripts/deploy_dokploy.cjs',archive.namelist())
                self.assertNotIn('compose.yml',archive.namelist())
                self.assertNotIn('compose.security.yml',archive.namelist())
                workflow=archive.read('.github/workflows/deploy-dokploy.yml').decode()
                self.assertIn("vars.DOKPLOY_DEPLOY_ENABLED == 'true'",workflow)
                self.assertIn("if: needs.authorize.outputs.allowed == 'true'",workflow)
                self.assertIn('ref: ${{ env.DEPLOY_SHA }}',workflow)
                self.assertIn("require('./.devsecops/engine/scripts/deploy_dokploy.cjs')",workflow)
                self.assertIn('persist-credentials: false',workflow)
                guide=archive.read('SECURITY_SETUP.md').decode()
                for name in ['DOKPLOY_URL','DOKPLOY_COMPOSE_ID','DOKPLOY_API_KEY','DOKPLOY_DEPLOY_ENABLED','DOKPLOY_COMPOSE_PATH']:
                    self.assertIn(name,guide)
                self.assertIn('puerto interno',guide)
                self.assertIn('Desactiva Auto Deploy',guide)
                self.assertIn('No pulses Deploy',guide)
                self.assertFalse(json.loads(archive.read('.devsecops/manifest.json'))['capabilities']['localDashboard'])
            self.assertFalse((root/'.github').exists())
