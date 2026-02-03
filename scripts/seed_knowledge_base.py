"""Seed the knowledge base with sample automotive documentation."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import async_session
from src.rag.pipeline import RAGPipeline


# ============== Sample Documentation ==============

VEHICLE_SPECS = """
# Technical Specifications - GenAuto X1 2024

## Engine
- **Type**: 1.0 TSI Turbo Flex
- **Power**: 128 hp (gasoline) / 116 hp (ethanol)
- **Torque**: 200 Nm
- **Displacement**: 999 cc
- **Fuel System**: Direct fuel injection
- **Fuel**: Flex (gasoline/ethanol)

## Transmission
- **Type**: 6-speed automatic
- **Drive**: Front-wheel drive
- **Driving Modes**: Normal, Sport, Eco

## Dimensions
- **Length**: 4,199 mm (165.3 in)
- **Width**: 1,760 mm (69.3 in)
- **Height**: 1,568 mm (61.7 in)
- **Wheelbase**: 2,651 mm (104.4 in)
- **Cargo Capacity**: 373 liters (420L with rear seats folded)

## Weight and Capacities
- **Curb Weight**: 1,239 kg (2,731 lbs)
- **Fuel Tank Capacity**: 50 liters (13.2 gal)
- **Towing Capacity**: 750 kg (1,653 lbs) braked

## Fuel Economy (EPA Equivalent)
- **City (gasoline)**: 29 mpg
- **Highway (gasoline)**: 34 mpg
- **City (ethanol)**: 20 mpg
- **Highway (ethanol)**: 24 mpg

## Tires and Wheels
- **Tire Size**: 205/60 R16
- **Wheels**: 16" alloy
- **Spare**: Temporary (emergency use only, max 50 mph)
"""

MAINTENANCE_GUIDE = """
# Maintenance Guide - GenAuto X1

## Scheduled Maintenance

### 10,000 km (6,000 mi) or 12 months Service
- Engine oil change
- Oil filter replacement
- Air filter inspection
- Brake inspection
- Fluid level check
- **Estimated Cost**: $150

### 20,000 km (12,000 mi) or 24 months Service
- All items from 10,000 km service
- Engine air filter replacement
- Cabin air filter replacement
- Belt inspection
- Wheel alignment and balancing
- **Estimated Cost**: $220

### 40,000 km (24,000 mi) or 48 months Service
- All previous items
- Spark plug replacement
- Brake fluid replacement
- Suspension inspection
- **Estimated Cost**: $320

### 60,000 km (36,000 mi) Service
- All previous items
- Alternator belt replacement
- Cooling system inspection
- Exhaust system inspection
- **Estimated Cost**: $400

## Replacement Intervals

| Item | Interval |
|------|----------|
| Engine oil | 10,000 km or 12 months |
| Oil filter | 10,000 km or 12 months |
| Air filter | 20,000 km or 24 months |
| Fuel filter | 40,000 km |
| Spark plugs | 40,000 km |
| Brake fluid | 40,000 km or 24 months |
| Coolant | 60,000 km or 48 months |
| Timing belt | 100,000 km |

## Recommended Oil
- **Specification**: SAE 5W-30 API SN
- **Capacity with filter**: 4.2 liters (4.4 qt)
- **Approved Brands**: Castrol, Mobil, Shell, Petronas
"""

TROUBLESHOOTING_GUIDE = """
# Troubleshooting Guide - Common Problems

## Check Engine Light On

### Common Causes
1. **Loose Gas Cap**
   - Symptom: Light comes on after refueling
   - Solution: Check and tighten gas cap
   - Severity: Low

2. **Oxygen Sensor (Lambda Sensor)**
   - Symptom: Increased fuel consumption, rough idle
   - Solution: Sensor replacement
   - Average Cost: $100-170
   - Severity: Medium

3. **Catalytic Converter**
   - Symptom: Power loss, sulfur smell
   - Solution: Inspection and possible replacement
   - Severity: High (seek service immediately)

4. **Ignition Coil**
   - Symptom: Engine misfires, power loss
   - Solution: Diagnosis and replacement of faulty coil
   - Severity: Medium

## Brake Issues

### Brake Making Noise
- **Squealing when braking**: Brake pads may be worn
  - Check pad thickness (minimum 3mm)
  - Replace if necessary
  
- **Metallic grinding**: Rotor may be warped or worn
  - Check rotor thickness
  - Resurface or replace

### Soft Brake Pedal
- Check brake fluid level
- Possible air in system (bleeding required)
- Check master cylinder
- **WARNING**: Do not drive with compromised brakes!

## Engine Overheating

### Immediate Actions
1. Turn heater to maximum (helps dissipate heat)
2. Turn off air conditioning
3. Pull over safely
4. NEVER open reservoir while engine is hot
5. Wait to cool down (minimum 30 minutes)

### Common Causes
- Low coolant level
- System leak
- Stuck thermostat
- Failed cooling fan
- Faulty water pump

## Dead Battery

### How to Jump Start
1. Connect red (+) cable to good battery
2. Connect other end of red (+) to dead battery
3. Connect black (-) cable to good battery
4. Connect other end of black to engine ground (metal surface)
5. Start car with good battery
6. Wait 2-3 minutes
7. Try starting car with dead battery
8. Remove cables in reverse order

### Signs of Weak Battery
- Slow cranking
- Dim lights
- Electrical system failures
- Battery over 3 years old
"""

FEATURES_GUIDE = """
# Features Guide - GenAuto X1 2024

## GenConnect 10" Infotainment System

### Connectivity
- **Android Auto**: Connect your Android phone via USB cable
- **Apple CarPlay**: Connect your iPhone via USB cable
- **Bluetooth**: Pair up to 8 devices
- **Wi-Fi**: Integrated hotspot (requires data plan)

### Screen Mirroring
1. Connect USB cable to center console port
2. Authorize connection on phone
3. Mirroring will start automatically

### Voice Commands
Activate by saying "Ok GenAuto" or pressing the steering wheel button:
- "Call [contact]"
- "Navigate to [address]"
- "Play [music/artist]"
- "Set temperature to [degrees]"

## Adaptive Cruise Control (ACC)

### Activation
1. Accelerate to desired speed (minimum 20 mph)
2. Press SET button on steering wheel
3. Adjust following distance (3 levels)
4. To deactivate: press brake or OFF button

### Limitations
- Does not work below 20 mph
- Sharp curves may deactivate system
- Heavy rain may interfere with sensors
- Always keep hands on steering wheel

## Parking Assistant

### How to Use
1. Activate turn signal toward parking space
2. Drive past space at low speed (<12 mph)
3. When "P" appears on dash, stop vehicle
4. Select detected space
5. Release steering wheel, control only pedals
6. System will perform maneuver automatically

### Supported Space Types
- Parallel parking
- Perpendicular (90°)
- Angled (45°)

## Sensors and Cameras

### Parking Sensors
- 4 front sensors
- 4 rear sensors
- Progressive audio alert
- Graphic display on infotainment

### Rear Camera
- HD resolution
- Dynamic guide lines
- Motion sensor
- Activates automatically in reverse

### 360° Camera
- Top-down vehicle view
- 4 synchronized cameras
- Useful for tight space maneuvers
"""

FAQ_CONTENT = """
# Frequently Asked Questions - GenAuto X1

## Warranty

**Q: What is the vehicle warranty period?**
A: The GenAuto X1 has a 3-year or 60,000-mile warranty (whichever comes first), valid for manufacturing defects.

**Q: Does the warranty cover normal wear?**
A: No. Wear items such as brake pads, tires, wiper blades, and clutch are not covered by warranty.

**Q: Can I service outside the dealership without voiding warranty?**
A: Yes, as long as you use genuine parts and follow the maintenance schedule in the manual. Keep all receipts.

## Fuel

**Q: Can I use premium gasoline?**
A: Yes, premium gasoline can be used and helps keep the injection system clean.

**Q: What's the performance difference between gasoline and ethanol?**
A: With ethanol, power is slightly lower (116hp vs 128hp), but torque is similar. Fuel consumption with ethanol is approximately 30% higher.

**Q: What happens if I mix gasoline and ethanol?**
A: No problem. The flex system automatically adapts to any mixture ratio.

## Tires

**Q: What is the correct tire pressure?**
A: Front: 32 psi / Rear: 32 psi (normal load). For maximum load: 35 psi.

**Q: Can I use different size tires?**
A: Not recommended. Always use the original size (205/60 R16) to maintain safety and not void warranty.

**Q: Is the spare tire for temporary use?**
A: Yes. The temporary spare should only be used in emergencies, with maximum speed of 50 mph and maximum distance of 50 miles.

## Technology

**Q: How do I update the infotainment system?**
A: Updates are done automatically via Wi-Fi or at the dealership during services.

**Q: Does the car have a tracker?**
A: Yes, the GenAuto X1 has an integrated tracker. Activate the service through the GenAuto Connect app.

**Q: How does the proximity key work?**
A: With the key in your pocket, approach the vehicle to unlock automatically. To start, press the Start/Stop button with foot on brake.

## Maintenance

**Q: How often should I change the oil?**
A: Every 10,000 km (6,000 mi) or 12 months, whichever comes first.

**Q: What oil should I use?**
A: SAE 5W-30 with API SN specification or higher.

**Q: Does the timing belt need replacement?**
A: Yes, every 100,000 km (60,000 mi) or as indicated by the onboard computer.
"""

SAFETY_GUIDE = """
# Safety Manual - GenAuto X1

## Safety Equipment

### Airbags
The vehicle has 6 airbags:
- 2 frontal (driver and passenger)
- 2 side (driver and passenger)
- 2 curtain (head protection)

**WARNING**: 
- Never install child seat in front passenger seat
- Children under 12 should ride in rear seat
- Do not place objects on dashboard or airbags

### Seat Belts
- All belts are 3-point with retractor
- Front belts have pretensioners
- Audio and visual alert for unfastened belts

### Driver Assistance Systems (ADAS)

**Automatic Emergency Braking (AEB)**
- Detects obstacles and pedestrians
- Alerts driver
- Brakes automatically if no reaction
- Works between 3-50 mph

**Forward Collision Warning (FCW)**
- Monitors vehicles ahead
- Visual and audio alert
- Prepares braking system

**Lane Keep Assist (LKA)**
- Detects lane markings
- Alerts if leaving lane without signaling
- Can gently correct steering

**Blind Spot Monitoring (BSM)**
- Sensors in side mirrors
- Visual alert when vehicle in blind spot
- Especially useful for lane changes

## Child Safety Seats

### ISOFIX Mounting
The vehicle has ISOFIX anchor points on outer rear seats:
- 2 lower anchor points
- 1 Top Tether point (upper)

### Recommendation by Age
- Under 1 year: Rear-facing infant seat
- 1-4 years: Forward-facing child seat
- 4-8 years: Booster seat with back
- 8-12 years: Booster seat (backless)

## In Case of Accident

### Procedures
1. Stay calm
2. Turn on hazard lights
3. Set up warning triangle (100 ft from vehicle)
4. Check for injuries
5. Call emergency services: 911
6. Do not move injured persons (except fire risk)
7. File police report

### Emergency Contacts
- GenAuto 24h Roadside Assistance: 1-800-XXX-XXXX
- Emergency Services: 911
- Police: 911
- Fire Department: 911
"""


DOCUMENTS = [
    {
        "text": VEHICLE_SPECS,
        "source": "specs_genautox1_2024.md",
        "document_type": "spec",
    },
    {
        "text": MAINTENANCE_GUIDE,
        "source": "maintenance_guide_genautox1.md",
        "document_type": "manual",
    },
    {
        "text": TROUBLESHOOTING_GUIDE,
        "source": "troubleshooting_guide.md",
        "document_type": "troubleshoot",
    },
    {
        "text": FEATURES_GUIDE,
        "source": "features_guide_genautox1.md",
        "document_type": "guide",
    },
    {
        "text": FAQ_CONTENT,
        "source": "faq_genautox1.md",
        "document_type": "faq",
    },
    {
        "text": SAFETY_GUIDE,
        "source": "safety_manual_genautox1.md",
        "document_type": "manual",
    },
]


async def seed_knowledge_base():
    """Seed the knowledge base with sample documentation."""
    print("🚗 GenAI Auto - Knowledge Base Seeder")
    print("=" * 50)

    async with async_session() as db:
        pipeline = RAGPipeline(db)

        # Check current stats
        stats = await pipeline.get_stats()
        print(f"\n📊 Current stats: {stats['total_chunks']} chunks, {stats['total_sources']} sources")

        if stats['total_chunks'] > 0:
            response = input("\n⚠️  Knowledge base already has data. Clear and reseed? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return

            # Clear existing data
            print("\n🗑️  Clearing existing data...")
            for doc in DOCUMENTS:
                await pipeline.delete_document(doc["source"])
            print("   Done!")

        print("\n📥 Ingesting documents...\n")

        total_chunks = 0
        total_tokens = 0

        for doc in DOCUMENTS:
            print(f"   📄 {doc['source']}...")
            
            result = await pipeline.ingest_text(
                text=doc["text"],
                source=doc["source"],
                document_type=doc["document_type"],
            )
            
            total_chunks += result["chunks_created"]
            total_tokens += result["tokens_used"]
            
            print(f"      ✅ {result['chunks_created']} chunks, {result['tokens_used']} tokens")

        print("\n" + "=" * 50)
        print(f"✨ Seeding complete!")
        print(f"   📚 Documents: {len(DOCUMENTS)}")
        print(f"   📦 Total chunks: {total_chunks}")
        print(f"   🎯 Total tokens: {total_tokens}")

        # Show final stats
        final_stats = await pipeline.get_stats()
        print(f"\n📊 Final stats: {final_stats}")


if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())
