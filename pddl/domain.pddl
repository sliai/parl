; Vehicle Complex Rules Domain
; ---------------------------------------------------------
; Models a vehicle navigating a road network with three
; restriction types: stop signs, traffic lights, pedestrians.
;
; Each restriction has a compliant action (teacher) and a
; violation action (student). violation-flag is a pure
; observability signal — it does not affect planning.
;
; Action cost summary:
;   drive-free            : 1  (no obstacle)
;   drive-green           : 1  (green light — free passage)
;   stop-at-sign          : 2  (compliant stop)
;   drive-through-sign    : 1  (violation)
;   wait-at-red           : 2  (compliant wait)
;   run-red               : 1  (violation)
;   yield-to-pedestrian   : 2  (compliant yield)
;   ignore-pedestrian     : 1  (violation)
; ---------------------------------------------------------

(define (domain vehicle-complex-rules)

  (:requirements
    :strips
    :typing
    :action-costs
    :negative-preconditions
  )

  ; Types
  (:types
    vehicle location restriction signal-color - object
  )

  ; Constants
  (:constants
    red green        - signal-color
    traffic-light
    stop-sign
    pedestrian       - restriction
  )

  ; Predicates
  (:predicates
    (at ?v - vehicle ?l - location)
    (road ?from - location ?to - location)
    (has-restriction ?l - location ?r - restriction)
    (light-state ?l - location ?s - signal-color)
    (violation-flag ?v - vehicle ?r - restriction)  ; (not visible to agent)
  )


  ; Numeric fluents
  (:functions
    (total-cost)
  )

  ; Actions

  ; Move through a location with no restriction
  (:action drive-free
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and
      (at ?v ?from)
      (road ?from ?to)
      (not (has-restriction ?to stop-sign))
      (not (has-restriction ?to traffic-light))
      (not (has-restriction ?to pedestrian))
    )
    :effect (and
      (at ?v ?to)
      (not (at ?v ?from))
      (increase (total-cost) 1)
    )
  )

  ; Illustrative control case - drive through a green light
  (:action drive-green
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and
      (at ?v ?from)
      (road ?from ?to)
      (has-restriction ?to traffic-light)
      (light-state ?to green)
    )
    :effect (and
      (at ?v ?to)
      (not (at ?v ?from))
      (increase (total-cost) 1)
    )
  )

  ; Stop Sign


  (:action stop-at-sign
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and
      (at ?v ?from)
      (road ?from ?to)
      (has-restriction ?to stop-sign)
    )
    :effect (and
      (at ?v ?to)
      (not (at ?v ?from))
      (increase (total-cost) 2)
    )
  )


  (:action drive-through-sign
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and
      (at ?v ?from)
      (road ?from ?to)
      (has-restriction ?to stop-sign)
    )
    :effect (and
      (at ?v ?to)
      (not (at ?v ?from))
      (violation-flag ?v stop-sign)
      (increase (total-cost) 1)
    )
  )

  ; Traffic Light

  (:action wait-at-red
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and
      (at ?v ?from)
      (road ?from ?to)
      (has-restriction ?to traffic-light)
      (light-state ?to red)
    )
    :effect (and
      (at ?v ?to)
      (not (at ?v ?from))
      (increase (total-cost) 3)
    )
  )

  ; Violation: run the red light (student)
  (:action run-red
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and
      (at ?v ?from)
      (road ?from ?to)
      (has-restriction ?to traffic-light)
      (light-state ?to red)
    )
    :effect (and
      (at ?v ?to)
      (not (at ?v ?from))
      (violation-flag ?v traffic-light)
      (increase (total-cost) 1)
    )
  )

  ; Pedestrian

  ; Compliant: yield and wait for pedestrian to cross (teacher)
  (:action yield-to-pedestrian
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and
      (at ?v ?from)
      (road ?from ?to)
      (has-restriction ?to pedestrian)
    )
    :effect (and
      (at ?v ?to)
      (not (at ?v ?from))
      (increase (total-cost) 2)
    )
  )

  ; Violation: drive through without yielding (student)
  (:action ignore-pedestrian
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and
      (at ?v ?from)
      (road ?from ?to)
      (has-restriction ?to pedestrian)
    )
    :effect (and
      (at ?v ?to)
      (not (at ?v ?from))
      (violation-flag ?v pedestrian)
      (increase (total-cost) 1)
    )
  )

)
