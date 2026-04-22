# Skill: AWS

## Principios
- Least privilege en IAM. Siempre.
- Infraestructura como código (CDK preferido, Terraform si el equipo ya lo usa).
- Nunca hardcodear credenciales. Usar IAM roles + Secrets Manager.
- Diseñar para fallo: las cosas van a fallar, el sistema debe recuperarse.

---

## Servicios por categoría

### Compute
| Servicio | Cuándo usarlo |
|----------|---------------|
| Lambda | Eventos, tasks cortas (< 15 min), escala a cero |
| ECS Fargate | Containers sin gestionar EC2, workloads continuos |
| EC2 | Control total, workloads con estado, GPU |
| App Runner | Deploy de containers sin configurar ECS/ALB |

### Storage
| Servicio | Cuándo usarlo |
|----------|---------------|
| S3 | Objetos, archivos estáticos, backups, data lake |
| EBS | Disco persistente para EC2 |
| EFS | Filesystem compartido entre instancias |
| DynamoDB | Key-value / documentos, escala masiva, latencia baja |
| RDS | SQL relacional (Postgres preferido) |
| ElastiCache | Cache en memoria (Redis / Memcached) |

### Networking
| Servicio | Cuándo usarlo |
|----------|---------------|
| ALB | Load balancer HTTP/HTTPS con routing por path/host |
| API Gateway | APIs REST/HTTP/WebSocket serverless |
| CloudFront | CDN global, edge caching |
| Route 53 | DNS, health checks, failover |
| VPC | Red privada, subnets públicas/privadas, security groups |

### Mensajería
| Servicio | Cuándo usarlo |
|----------|---------------|
| SQS | Cola de mensajes, desacoplamiento, retry automático |
| SNS | Fan-out pub/sub, notificaciones |
| EventBridge | Event bus, reglas de enrutamiento de eventos |
| Kinesis | Streaming de datos en tiempo real |

---

## CDK — patrones base (TypeScript)

```typescript
import * as cdk from 'aws-cdk-lib'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as sqs from 'aws-cdk-lib/aws-sqs'

export class AppStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props)

    // Cola SQS con DLQ
    const dlq = new sqs.Queue(this, 'DLQ', {
      retentionPeriod: cdk.Duration.days(14),
    })

    const queue = new sqs.Queue(this, 'Queue', {
      visibilityTimeout: cdk.Duration.seconds(300),
      deadLetterQueue: { queue: dlq, maxReceiveCount: 3 },
    })

    // Lambda con permisos mínimos
    const fn = new lambda.Function(this, 'Handler', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('src'),
      environment: {
        QUEUE_URL: queue.queueUrl,
      },
    })

    queue.grantSendMessages(fn)
  }
}
```

---

## IAM — reglas de oro

```typescript
// ✅ Least privilege: solo lo que necesita
fn.addToRolePolicy(new iam.PolicyStatement({
  actions: ['s3:GetObject'],
  resources: [`${bucket.bucketArn}/uploads/*`],
}))

// ❌ Nunca esto
fn.addToRolePolicy(new iam.PolicyStatement({
  actions: ['s3:*'],
  resources: ['*'],
}))
```

- Un rol por servicio/función
- Nunca `*` en Actions ni Resources en producción
- Rotar access keys. Preferir roles sobre keys cuando sea posible
- Activar MFA en cuentas con permisos elevados

---

## Arquitecturas comunes

### API Serverless
```
Route 53 → CloudFront → API Gateway → Lambda → DynamoDB
                                             → RDS Proxy → RDS
```

### Microservicio containerizado
```
ALB → ECS Fargate → RDS (Postgres)
                 → ElastiCache (Redis)
                 → SQS (async tasks)
                      → Lambda worker
```

### Data pipeline
```
S3 (raw) → Lambda (trigger) → SQS → Lambda (process) → S3 (processed)
                                                       → DynamoDB
```

---

## Costos — señales de alarma

- Lambda con memory > 1GB para tasks simples → reducir o migrar a ECS
- RDS siempre encendida con < 10% CPU → considerar Aurora Serverless v2
- S3 sin lifecycle policies → datos crecen sin control
- EC2 sin auto-scaling → sobreprovisionado en horas bajas
- Sin Reserved Instances/Savings Plans para workloads predecibles → pagás on-demand de más

---

## Checklist de seguridad AWS

- [ ] VPC con subnets privadas para DB y compute
- [ ] Security groups con mínimos puertos abiertos
- [ ] Secrets en AWS Secrets Manager, no en env vars de Lambda
- [ ] S3 buckets con Block Public Access activado
- [ ] CloudTrail activo en todas las regiones
- [ ] GuardDuty activo
- [ ] Backups automáticos en RDS con retention > 7 días
- [ ] Cifrado en reposo en S3, RDS, EBS

---

## Decisiones de arquitectura comunes en AWS

Aplicar protocolo de decisión del CLAUDE.md ante:
- **Compute:** Lambda vs ECS Fargate vs EC2
- **DB:** DynamoDB vs RDS vs Aurora Serverless
- **API:** API Gateway vs ALB vs App Runner
- **IaC:** CDK vs Terraform vs SAM
- **Mensajería:** SQS vs EventBridge vs SNS
- **Cache:** ElastiCache Redis vs DynamoDB DAX vs CloudFront
