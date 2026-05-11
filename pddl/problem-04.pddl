; Problem 4 — Stop Sign + Red Light + Green Light (control)
; ---------------------------------------------------------
; Route:  start --> sign-zone --> green-light-zone --> red-light-zone --> destination
;
; The green light is a control case — both teacher and student
; take drive-green here. It should NOT appear in T_CR because
; the teacher never deviates at a green light.
;
; Teacher plan:
;   stop-at-sign -> drive-green -> wait-at-red -> drive-free   cost: 7
; Student assumed optimal plan:
;   drive-through-sign -> drive-green -> run-red -> drive-free  cost: 4
;
; PARL signal:
;   step 1: stop-at-sign taken,  drive-through-sign omitted => stop-sign to T_CR
;   step 2: drive-green taken,   drive-green taken           => no deviation
;   step 3: wait-at-red taken,   run-red omitted             => traffic-light to T_CR
;   drive-green observed in T_O — does not end up in T_R
; ---------------------------------------------------------

(define (problem prob-04-sign-and-light)
  (:domain vehicle-complex-rules)

  (:objects
    car                                                          - vehicle
    start sign-zone green-light-zone red-light-zone destination  - location
  )

  (:init
    (at car start)

    (road start sign-zone)
    (road sign-zone green-light-zone)
    (road green-light-zone red-light-zone)
    (road red-light-zone destination)

    (has-restriction sign-zone stop-sign)
    (has-restriction green-light-zone traffic-light)
    (has-restriction red-light-zone traffic-light)

    (light-state green-light-zone green)
    (light-state red-light-zone red)

    (= (total-cost) 0)
  )

  (:goal (at car destination))
  (:metric minimize (total-cost))
)
