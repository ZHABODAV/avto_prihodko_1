# Architecture Evolution

This document illustrates the evolution of the Terminal Optimizer architecture, highlighting the transition from a deterministic, manual-input system to a robust, optimized planner.

## State: WAS (Deterministic & Reactive)

The initial system was a direct calculator that translated inputs into a schedule without optimization or robustness checks.

```mermaid
layerBlock
    block: Business_Logic
        BL1["Push Model"]
        BL2["Manual Grouping"]
        BL3["Single Scenario"]
    end
    
    block: Math_Basis
        M1["Deterministic Arithmetic"]
        M2["Linear Sequencing"]
    end
    
    block: Functions
        F1["Generate Sequence"]
        F2["Calculate Balances"]
    end
    
    block: Implementation
        I1["Simple Loop"]
        I2["No Buffers"]
    end
    
    BL1 --> M1
    M1 --> F1
    F1 --> I1
```

## State: NOW (Robust & Optimized)

The enhanced system incorporates simulation, buffering, and optimization logic to handle real-world variability.

```mermaid
layerBlock
    block: Business_Logic
        BL1["Robust Planning"]
        BL2["Cost Optimization"]
        BL3["Risk Aware"]
    end
    
    block: Math_Basis
        M1["Monte Carlo Simulation"]
        M2["Bin Packing (Wagons)"]
        M3["Probabilistic Analysis"]
    end
    
    block: Functions
        F1["Simulate Scenarios"]
        F2["Optimize Batches"]
        F3["Apply Buffers"]
    end
    
    block: Implementation
        I1["MonteCarloSimulator"]
        I2["WagonManager.distribute"]
        I3["Time Delta Buffers"]
    end
    
    BL1 --> M1
    M1 --> F1
    F1 --> I1
    
    BL2 --> M2
    M2 --> F2
    F2 --> I2
```

## Key Improvements

1.  **Robustness:** Added time buffers and Monte Carlo simulation to handle variability.
2.  **Optimization:** Implemented wagon batching to reduce costs and logistical complexity.
3.  **Confidence:** Provides a confidence score for generated plans.
