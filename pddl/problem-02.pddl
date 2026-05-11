; Problem 2 — Single Red Traffic Light
; ---------------------------------------------------------
; Route:  start --> light-zone --> destination
;
; Teacher plan:  wait-at-red -> drive-free     cost: 4
; Student assummed optimal plan:  run-red -> drive-free          cost: 2
;
; PARL signal: wait-at-red taken, run-red omitted
;              => traffic-light added to T_CR
; ---------------------------------------------------------

(define (problem prob-02-red-light)
  (:domain vehicle-complex-rules)

  (:objects
    car                              - vehicle
    start light-zone destination     - location
  )

  (:init
    (at car start)

    (road start light-zone)
    (road light-zone destination)

    (has-restriction light-zone traffic-light)
    (light-state light-zone red)

    (= (total-cost) 0)
  )

  (:goal (at car destination))
  (:metric minimize (total-cost))
)
