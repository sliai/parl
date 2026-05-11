; Problem 1 — Single Stop Sign
; ---------------------------------------------------------
; Route:  start --> sign-zone --> destination
;
; Teacher plan:  stop-at-sign  -> drive-free     cost: 3
; Student assumed optimal plan:  drive-through-sign -> drive-free cost: 2
;
; PARL signal: stop-at-sign taken, drive-through-sign omitted
;              => stop-sign added to T_CR
; ---------------------------------------------------------s

(define (problem prob-01-stop-sign)
  (:domain vehicle-complex-rules)

  (:objectsst
    car                             - vehicle
    start sign-zone destination     - location
  )

  (:init
    (at car start)

    (road start sign-zone)
    (road sign-zone destination)

    (has-restriction sign-zone stop-sign)

    (= (total-cost) 0)
  )

  (:goal (at car destination))
  (:metric minimize (total-cost))
)
