"""Run one idempotent daily monitoring batch; suitable for an external scheduler."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import engine, monitoring

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=['business_drop', 'late_data', 'recovered'], default='business_drop')
    args = parser.parse_args()
    engine.initialize()
    print(json.dumps(monitoring.run_check(args.scenario), ensure_ascii=False, indent=2))
