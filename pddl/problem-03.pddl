; Problem 3 — Single Pedestrian Crossing
; ---------------------------------------------------------
; Route:  start --> crosswalk --> destination
;
; Teacher plan:  yield-to-pedestrian -> drive-free    cost: 3
; Student assumed optimal plan:  ignore-pedestrian -> drive-free       cost: 2
;
; PARL signal: yield-to-pedestrian taken, ignore-pedestrian omitted
;              => pedestrian added to T_CR
; ---------------------------------------------------------

(define (problem prob-03-pedestrian)
  (:domain vehicle-complex-rules)

  (:objects
    car                               - vehicle
    start crosswalk destination       - location
  )

  (:init
    (at car start)

    (road start crosswalk)
    (road crosswalk destination)

    (has-restriction crosswalk pedestrian)

    (= (total-cost) 0)
  )

  (:goal (at car destination))
  (:metric minimize (total-cost))
)
