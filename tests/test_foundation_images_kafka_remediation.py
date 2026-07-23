import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "deploy/compose/derived-images/recipes.json"


class KafkaRemediationRecipeTests(unittest.TestCase):
    def test_kafka_recipe_remediates_fixable_jetty_security_high(self) -> None:
        # Given: the repository's locked foundation image recipe manifest.
        repository_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

        # When: the Kafka derivative recipe and Dockerfile are inspected.
        kafka = next(
            item for item in repository_manifest["recipes"]
            if item["component"] == "kafka"
        )
        dockerfile = (MANIFEST.parent / kafka["dockerfile"]).read_text(
            encoding="utf-8",
        )

        # Then: the recipe replaces the fixable Jetty security artifact.
        expected_sha256 = (
            "e6fb70974291312c58ac84d8bf28c909d1800d1b3104020e7cd4db77391f9fb2"
        )
        self.assertEqual("4.3.1-r3", kafka["output_tag"])
        self.assertIn(
            {
                "filename": "jetty-security-12.0.36.jar",
                "url": (
                    "https://repo.maven.apache.org/maven2/org/eclipse/jetty/"
                    "jetty-security/12.0.36/jetty-security-12.0.36.jar"
                ),
                "sha256": expected_sha256,
                "context": True,
            },
            kafka["inputs"],
        )
        self.assertIn(
            {
                "finding": "CVE-2026-10050",
                "artifact": "jetty-security",
                "from_version": "12.0.34",
                "to_version": "12.0.36",
                "sha256": expected_sha256,
            },
            kafka["patches"],
        )
        self.assertIn("rm /opt/kafka/libs/jetty-security-12.0.34.jar", dockerfile)
        self.assertIn(
            "install -o root -g root -m 0444 /tmp/jetty-security-12.0.36.jar "
            "/opt/kafka/libs/jetty-security-12.0.36.jar",
            dockerfile,
        )
        self.assertIn('io.dcim.recipe.revision="3"', dockerfile)
        self.assertIn('org.opencontainers.image.version="4.3.1-dcim.3"', dockerfile)
        self.assertIn('io.dcim.remediation.jetty-security="12.0.36"', dockerfile)


if __name__ == "__main__":
    unittest.main()
