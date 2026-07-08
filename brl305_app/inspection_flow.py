"""Per-roll inspection orchestration, with NO Tk dependency so it is fully unit-testable.
The Tk panel is a thin view over this controller."""
from defect_map import build_defect_rows


class InspectionController:
    def __init__(self, client, outbox, defect_map):
        self.client = client
        self.outbox = outbox
        self.defect_map = defect_map

    def load_roll(self, work_order, roll_no):
        """DOWN: resolve the Quality-Check Job Card and pull its context + defect panel."""
        job_card = self.client.resolve_job_card(work_order, roll_no)
        return job_card, self.client.get_context(job_card)

    def queue_save(self, job_card, length, weight, machine_defects, context, deep_scan):
        """Build the save payload and enqueue it. Only deep-scanned rolls carry defects.
        Returns (rows, unmapped) so the view can prompt the operator to classify unmapped."""
        points_by_type = {dt["name"]: dt.get("points", 0)
                          for dt in context.get("defect_types", [])}
        source = machine_defects if deep_scan else []
        rows, unmapped = build_defect_rows(source, self.defect_map, points_by_type)
        payload = {"inspection_length": length, "fabric_weight": weight, "defects": rows}
        self.outbox.enqueue("save", job_card, payload)
        return rows, unmapped

    def queue_finalize(self, job_card):
        self.outbox.enqueue("finalize", job_card, {})

    def sender(self, kind, job_card, payload):
        """UP: called by outbox.drain for each queued item."""
        if kind == "save":
            self.client.save_inspection(job_card, payload["inspection_length"],
                                        payload["fabric_weight"], payload["defects"])
        elif kind == "finalize":
            self.client.finalize_inspection(job_card)
        else:
            raise ValueError("unknown kind: {}".format(kind))
