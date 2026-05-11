; Problem 5 — Full Route, All Restriction Types
; ---------------------------------------------------------
; Route (7 locations):
;
;   start --> zone-a --> zone-b --> zone-c --> zone-d --> zone-e --> destination
;
;   zone-a : stop sign
;   zone-b : free road
;   zone-c : red traffic light
;   zone-d : pedestrian crossing
;   zone-e : free road
;
; Teacher plan:
;   stop-at-sign(start->zone-a)          cost 2
;   drive-free(zone-a->zone-b)           cost 1
;   wait-at-red(zone-b->zone-c)          cost 3
;   yield-to-pedestrian(zone-c->zone-d)  cost 2
;   drive-free(zone-d->zone-e)           cost 1
;   drive-free(zone-e->destination)      cost 1
;   total-cost: 10
;
; STudent assumed optimal plan:
;   drive-through-sign(start->zone-a)    cost 1
;   drive-free(zone-a->zone-b)           cost 1
;   run-red(zone-b->zone-c)              cost 1
;   ignore-pedestrian(zone-c->zone-d)    cost 1
;   drive-free(zone-d->zone-e)           cost 1
;   drive-free(zone-e->destination)      cost 1
;   total-cost: 6
;
; PARL signal across full trajectory:
;   zone-a: stop-at-sign taken, drive-through-sign omitted => stop-sign to T_CR
;   zone-b: drive-free taken,   drive-free taken            => no deviation
;   zone-c: wait-at-red taken,  run-red omitted             => traffic-light to T_CR
;   zone-d: yield taken,        ignore-pedestrian omitted   => pedestrian to T_CR
;   T_O never contains violation actions => T_R = {stop-sign, traffic-light, pedestrian}
; ---------------------------------------------------------

(define (problem prob-05-full-route)
  (:domain vehicle-complex-rules)

  (:objects
    car                                                              - vehicle
    start zone-a zone-b zone-c zone-d zone-e destination            - location
  )

  (:init
    (at car start)

    (road start zone-a)
    (road zone-a zone-b)
    (road zone-b zone-c)
    (road zone-c zone-d)
    (road zone-d zone-e)
    (road zone-e destination)

    ; zone-a : stop sign
    (has-restriction zone-a stop-sign)

    ; zone-b : free — no restriction predicate needed

    ; zone-c : red traffic light
    (has-restriction zone-c traffic-light)
    (light-state zone-c red)

    ; zone-d : pedestrian crossing
    (has-restriction zone-d pedestrian)

    ; zone-e : free

    (= (total-cost) 0)
  )

  (:goal (at car destination))
  (:metric minimize (total-cost))
)
